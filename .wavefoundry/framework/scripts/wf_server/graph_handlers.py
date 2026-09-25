"""Graph response handlers; registration and shared dependencies stay in server_impl."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence


def _graph_unavailable_fields(gq, layer: str, index) -> dict[str, Any]:
    diag = gq.graph_not_ready_diagnostic(layer, index)
    return {"diagnostics": [diag],
            "next_tools": diag.get("recovery_tools", ["index_build"]),
            "usage": diag.get("recovery_usage", "index_build(content='graph', mode='create')")}

def _graph_auto_rebuild_diagnostic(index: Any) -> list[dict[str, Any]]:
    """Wave 131bt (131e2): surface the GraphQueryIndex auto-rebuild diagnostic.

    Returns a single-element list when ``graph_query.load_graph()`` fired a
    synchronous rebuild for a stale GRAPH_BUILDER_VERSION; an empty list
    otherwise. Call sites can splat this unconditionally.
    """
    diag = getattr(index, "auto_rebuild_diagnostic", None)
    if not isinstance(diag, dict):
        return []
    return [diag]

def _attach_auto_rebuild_diag(envelope: dict[str, Any], index: Any) -> dict[str, Any]:
    """Wave 131bt (131e2): prepend the auto-rebuild diagnostic to an existing
    MCP response envelope. Mutates and returns the envelope so call sites
    can write ``return _attach_auto_rebuild_diag(_response("ok", data, ...), index)``.

    No-op when the index has no diagnostic (the common case post-rebuild
    when the cache has already verified). Idempotent — duplicate calls
    don't insert the diagnostic twice.
    """
    if envelope is None or not isinstance(envelope, dict):
        return envelope
    extras = _graph_auto_rebuild_diagnostic(index)
    if not extras:
        return envelope
    existing = envelope.get("diagnostics")
    if not isinstance(existing, list):
        existing = []
    # Idempotency: if the same diagnostic already at the head, skip.
    diag = extras[0]
    if existing and isinstance(existing[0], dict) and existing[0].get("code") == diag.get("code"):
        return envelope
    envelope["diagnostics"] = [diag, *existing]
    return envelope

def code_callhierarchy_response(
    root: Path,
    symbol: str,
    file: Optional[str] = None,
    direction: str = "both",
    context_depth: int = 0,
    include_external: bool = False,
) -> dict[str, Any]:
    """Return the call hierarchy for a symbol using the persisted graph.

    By default (``include_external=False``, wave 130ol), entries whose target
    is an external (non-project) symbol — surfaced as ``file: "external"`` with
    no line/snippet — are excluded from the ``outgoing``/``incoming`` lists.
    The response gains an ``external_outgoing_count`` / ``external_incoming_count``
    field showing how many were suppressed. Pass ``include_external=True`` to
    surface them inline for callers that want the full set.

    The default suppression reflects two realities: (1) external entries lack
    file/line/snippet so they can't be navigated, and (2) the pre-1.1.0 graph
    extractor over-produced external entries because its call-resolution heuristic
    bottomed out at ``external::<name>`` for every cross-file call (fixed in this
    wave by the cross-file resolution pass in graph_indexer). Operators
    inspecting call graphs benefit from a clean signal-only default.
    """
    from wf_server import server_impl
    if direction not in {"both", "outgoing", "incoming"}:
        return server_impl._response(
            "error", {"symbol": symbol, "direction": direction},
            diagnostics=[server_impl._diagnostic("invalid_arguments", f"direction must be 'both', 'outgoing', or 'incoming'; got '{direction}'.")],
            next_tools=[], usage="",
        )
    if not symbol or not symbol.strip():
        return server_impl._response(
            "error", {"symbol": symbol},
            diagnostics=[server_impl._diagnostic("invalid_arguments", "symbol must be a non-empty string.")],
            next_tools=[], usage="",
        )
    symbol = symbol.strip()

    gq = server_impl._load_graph_query()
    try:
        index = gq.get_query_index(root, layer="project")
    except Exception as exc:
        return server_impl._response(
            "error", {"symbol": symbol},
            diagnostics=[server_impl._diagnostic("graph_error", f"Failed to load graph: {exc}")],
            next_tools=["index_build"],
            usage="index_build(content='graph', mode='create')",
        )

    if not index.present:
        return server_impl._response(
            "error", {"symbol": symbol},
            **_graph_unavailable_fields(gq, "project", index),
        )

    # Resolve symbol — prefer file-qualified node when file is given
    node_id: Optional[str] = None
    if file:
        candidate = f"{file}::{symbol}"
        if index.get_node(candidate) is not None:
            node_id = candidate
    if node_id is None:
        node_id = index.resolve_symbol(symbol)

    if node_id is None:
        # Wave 1304x / 1304r: refresh-then-resolve before emitting suggestions
        new_index, refreshed_id = _graph_refresh_and_resolve(root, symbol)
        if refreshed_id is not None:
            index = new_index
            node_id = refreshed_id

    if node_id is None:
        suggestions = server_impl._suggest_near_symbols(index, symbol)
        data: dict[str, Any] = {"symbol": symbol, "node_id": None, "definition_file": None, "parser_used": "graph", "suggestions": suggestions}
        if direction in {"both", "outgoing"}:
            data["outgoing"] = []
        if direction in {"both", "incoming"}:
            data["incoming"] = []
        return server_impl._response(
            "ok", data,
            diagnostics=[server_impl._diagnostic(
                "graph_symbol_not_found",
                f"Symbol '{symbol}' does not resolve to a graph node (refresh attempted).",
                recovery_tools=["code_keyword", "index_build"],
                recovery_usage=f"code_keyword(query={symbol!r})",
            )],
            next_tools=["index_build"], usage="index_build(content='graph', mode='create')",
        )

    node = index.get_node(node_id) or {}
    definition_file = node.get("source_file") or (node_id.split("::")[0] if "::" in node_id else node_id)
    _cloc = node.get("source_location") or "0:0"
    try:
        _current_start = int(str(_cloc).split(":")[0])
    except (ValueError, IndexError):
        _current_start = 0

    data: dict[str, Any] = {
        "symbol": symbol,
        "node_id": node_id,
        "definition_file": definition_file,
        "parser_used": "graph",
    }

    # Wave 1sbfi (1sbfh): declared supertypes, calls-parity external handling —
    # project supertypes always listed; external supertype entries gated on
    # ``include_external`` with ALWAYS-ON suppressed counts (a class whose only
    # supertypes are external must never read as "no relationships" with no
    # signal). Absent entirely when the node declares no supertypes.
    try:
        _supers = index.supertype_summary(node_id)
    except AttributeError:
        _supers = None
    if _supers:
        _supers_out = dict(_supers)
        if not include_external:
            _supers_out.pop("external", None)
        data["supertypes"] = _supers_out

    community_lookup = _load_cluster_lookup_with_ids(root)

    def _node_entry(nid: str) -> dict[str, Any]:
        n = index.get_node(nid) or {}
        label = n.get("label") or (nid.split("::")[-1] if "::" in nid else nid)
        src = n.get("source_file") or (nid.split("::")[0] if "::" in nid else nid)
        loc = n.get("source_location") or "0:0"
        try:
            start_line = int(str(loc).split(":")[0])
        except (ValueError, IndexError):
            start_line = 0
        c_label, c_id = community_lookup.get(nid, (None, None))
        # Wave 1wpaj: `node_id` and `kind` join the presentation fields so a
        # consumer can apply the documented trust policy to an individual entry
        # without a second graph call. `relation` and `confidence` are edge
        # properties, not node properties, so the callers below attach them.
        return {
            "name": label, "file": src, "line": None, "snippet": None,
            "call_site": None,
            "node_id": nid, "kind": n.get("kind"),
            "community": c_label, "community_id": c_id, "_start_line": start_line,
        }

    def _attach_edge_trust(entry: dict[str, Any], edge: dict[str, Any]) -> dict[str, Any]:
        """Wave 1wpaj: carry per-edge trust onto a hierarchy entry.

        `confidence` is the field that actually discriminates on `calls` edges
        (RECEIVER_RESOLVED / CONSTRUCTION_RESOLVED / EXTRACTED). `relation` is
        constant for this response because the traversal filters to one
        relation; it is carried for forward compatibility and no discrimination
        claim rests on it.
        """
        entry["relation"] = edge.get("relation") or "calls"
        entry["confidence"] = edge.get("confidence")
        return entry

    # Accumulator for advice-pattern diagnostics emitted on the incoming branch.
    # Initialized before direction conditionals so the variable is always defined
    # at the final _response call regardless of the requested direction.
    advice_diagnostics: list[dict[str, Any]] = []
    # Wave 1p2q3 (1p2q9 B): collect the edges actually surfaced so we can
    # populate `attribution_counts_by_language` from them at the end.
    _attr_edges: list[dict[str, Any]] = []
    if direction in {"both", "outgoing"}:
        _, out_edges, _ = index.traverse(node_id, relations=["calls"], max_hops=1, direction="callees")
        _attr_edges.extend(out_edges or [])
        out_entries: list[tuple[str, dict[str, Any]]] = []
        for e in out_edges:
            tgt = e.get("target")
            if not isinstance(tgt, str):
                continue
            entry = _attach_edge_trust(_node_entry(tgt), e)
            # Wave 1p2q3 (1p2td post-ship feedback): propagate edge.self_edge_kind
            # from the underlying edge to the outgoing entry so consumers reading
            # code_callhierarchy's outgoing list see the overload classification
            # without re-querying the raw edge layer.
            sek = e.get("self_edge_kind")
            if sek:
                entry["self_edge_kind"] = sek
            out_entries.append((tgt, entry))
        # Batch: scan definition_file once for all non-external callees
        if definition_file:
            callee_names = [
                entry["name"] for tgt_id, entry in out_entries
                if not tgt_id.startswith("external::")
            ]
            all_out_sites = _scan_all_call_sites_in_file(root, callee_names, definition_file)
        else:
            all_out_sites = {}
        outgoing: list[dict[str, Any]] = []
        external_outgoing_count = 0
        for tgt_id, entry in out_entries:
            is_external = tgt_id.startswith("external::") or entry.get("file") == "external"
            if not is_external and entry["_start_line"] > 0:
                entry["line"] = entry["_start_line"]
            if not is_external and definition_file:
                sites = all_out_sites.get(entry["name"], [])
                ref = _first_call_site_at_or_after(sites, _current_start)
                if ref:
                    # Definition and invocation belong to different files.
                    # Keep the caller's text with its own source coordinates.
                    entry["call_site"] = {
                        "file": definition_file, "line": ref["line"],
                        "snippet": ref.get("snippet"),
                    }
            entry.pop("_start_line", None)
            if is_external:
                external_outgoing_count += 1
                if not include_external:
                    continue
            outgoing.append(entry)
        data["outgoing"] = outgoing
        data["external_outgoing_count"] = external_outgoing_count

    if direction in {"both", "incoming"}:
        _, in_edges, _ = index.traverse(node_id, relations=["calls"], max_hops=1, direction="callers")
        _attr_edges.extend(in_edges or [])
        incoming_raw: list[tuple[str, dict[str, Any]]] = []
        for e in in_edges:
            src = e.get("source")
            if not isinstance(src, str):
                continue
            entry = _attach_edge_trust(_node_entry(src), e)
            # Wave 1p2q3 (1p2td post-ship feedback): propagate edge.self_edge_kind
            # from the underlying edge to the incoming entry so consumers reading
            # code_callhierarchy's incoming list see the overload classification.
            sek = e.get("self_edge_kind")
            if sek:
                entry["self_edge_kind"] = sek
            incoming_raw.append((src, entry))

        # Group by source file — scan each file once
        by_file: dict[str, list[tuple[str, dict[str, Any]]]] = {}
        for src_id, entry in incoming_raw:
            f = entry.get("file", "")
            if f and not src_id.startswith("external::"):
                by_file.setdefault(f, []).append((src_id, entry))

        # Wave 130rj (130tw): for Java queries with class-qualified node_ids,
        # filter caller-side call sites whose receiver type doesn't match the
        # queried class. Suppresses phantom cross-class callers from
        # simple-name attribution (e.g. ``oos.writeObject(...)`` falsely
        # matching ``JSON.writeObject``).
        #
        # Wave 13129 (1312l delivery review): the filter is provably redundant
        # on graphs built by the v13+ indexer (1312l moved receiver-type
        # resolution to graph-build time, eliminating phantoms at the source).
        # Short-circuit on v13+ to avoid per-query AST walks; the defense-in-
        # depth path stays active for cached pre-bump graphs (builder_version
        # < 13 or absent) that operators haven't rebuilt yet.
        _expected_owner_class = _extract_java_owner_class_from_node_id(node_id)
        try:
            _graph_builder_version_int = int(index.builder_version) if index.builder_version else 0
        except (TypeError, ValueError):
            _graph_builder_version_int = 0
        _receiver_filter_redundant = _graph_builder_version_int >= 13
        # Use the resolved node's bare label for call-site scanning; the user's
        # `symbol` may be qualified ("JSON.writeObject") which would never match
        # bare identifier text. Falls back to symbol when label is absent.
        _scan_label = node.get("label") or symbol
        _excluded_caller_ids: set[str] = set()
        for source_file, file_entries in by_file.items():
            sites = _scan_call_sites_in_file(root, _scan_label, source_file)
            if not sites:
                continue
            _apply_receiver_filter = bool(
                _expected_owner_class
                and source_file.endswith(".java")
                and not _receiver_filter_redundant
            )
            # Sort callers by their definition start line to attribute call sites correctly
            sorted_entries = sorted(file_entries, key=lambda x: x[1].get("_start_line", 0))
            used_lines: set[int] = set()
            for i, (_src_id, entry) in enumerate(sorted_entries):
                start_line = entry.get("_start_line", 0)
                next_start = (
                    sorted_entries[i + 1][1].get("_start_line", 0)
                    if i + 1 < len(sorted_entries) else (10 ** 12)
                )
                # Call sites within this entry's method scope.
                in_scope = [
                    r for r in sites
                    if (r.get("line") or 0) >= start_line
                    and (r.get("line") or 0) < next_start
                    and (r.get("line") or 0) not in used_lines
                ]
                if _apply_receiver_filter and in_scope:
                    # Phantom-caller test: if EVERY in-scope call site has a
                    # definitive receiver-type mismatch, this caller is a
                    # simple-name attribution phantom — exclude it.
                    has_match_or_uncertain = any(
                        r.get("_receiver_type") is None
                        or r.get("_receiver_type") == _expected_owner_class
                        for r in in_scope
                    )
                    if not has_match_or_uncertain:
                        _excluded_caller_ids.add(_src_id)
                        continue
                    # Keep only matching-or-uncertain refs for line attribution.
                    in_scope = [
                        r for r in in_scope
                        if r.get("_receiver_type") is None
                        or r.get("_receiver_type") == _expected_owner_class
                    ]
                if not in_scope:
                    continue
                ref = in_scope[0]
                line = ref.get("line") or 0
                entry["line"] = line
                entry["snippet"] = ref.get("snippet")
                entry["call_site"] = {
                    "file": entry["file"], "line": line,
                    "snippet": ref.get("snippet"),
                }
                used_lines.add(line)
        if _excluded_caller_ids:
            incoming_raw = [
                (sid, entry) for sid, entry in incoming_raw
                if sid not in _excluded_caller_ids
            ]

        incoming = []
        external_incoming_count = 0
        for _src_id, entry in incoming_raw:
            entry.pop("_start_line", None)
            is_external = _src_id.startswith("external::") or entry.get("file") == "external"
            if is_external:
                external_incoming_count += 1
                if not include_external:
                    continue
            incoming.append(entry)
        data["incoming"] = incoming
        data["external_incoming_count"] = external_incoming_count

        # Wave 130rj — field feedback §2.3: AOP/advice empty-incoming detection.
        # When the response would report zero project-internal callers AND the
        # queried method carries an AOP advice annotation/attribute, surface
        # `caller_pattern: "advice"` plus an `advice_pattern_detected`
        # diagnostic so agents route to instrumentation/aspect declarations
        # rather than falling back to code_references (which also returns
        # nothing useful — callers are wired at weave time).
        if not incoming:
            queried_node = index.get_node(node_id) or {}
            annotations = queried_node.get("annotations") or []
            advice_tail_set = {
                # Java / ByteBuddy / AspectJ
                "Advice.OnMethodEnter", "Advice.OnMethodExit",
                "Around", "Before", "After", "AfterReturning", "AfterThrowing",
                # C# / PostSharp / Castle / MethodBoundary aspects (130tc)
                "OnEntry", "OnExit", "OnSuccess", "OnException",
                "OnMethodBoundaryAspect", "MethodBoundaryAspect",
                "MethodInterceptionAspect", "OnMethodInvokeAspect",
                "AroundAdvice", "BeforeAdvice", "AfterAdvice",
            }
            def _annotation_tail(name: str) -> str:
                # `org.aspectj.lang.annotation.Around` → `Around`;
                # `Advice.OnMethodEnter` stays as-is.
                segs = name.split(".")
                if len(segs) >= 2 and segs[-2] == "Advice":
                    return f"Advice.{segs[-1]}"
                return segs[-1]
            matched_advice = [
                _annotation_tail(str(a))
                for a in annotations
                if _annotation_tail(str(a)) in advice_tail_set
            ]
            if matched_advice:
                # The "advice class name" is the enclosing class — strip the
                # method-name leaf from the qualified node_id portion after `::`.
                qualified = node_id.split("::", 1)[1] if "::" in node_id else ""
                advice_class = qualified.rsplit(".", 1)[0] if "." in qualified else qualified
                data["caller_pattern"] = "advice"
                data["advice_annotations"] = matched_advice
                # Language-aware recovery hint: choose glob + framework
                # references based on whether annotations look Java-style or
                # C#-style. Heuristic: any matched advice tail in the C# set
                # suggests C#; otherwise default to Java.
                csharp_tails = {
                    "OnEntry", "OnExit", "OnSuccess", "OnException",
                    "OnMethodBoundaryAspect", "MethodBoundaryAspect",
                    "MethodInterceptionAspect", "OnMethodInvokeAspect",
                    "AroundAdvice", "BeforeAdvice", "AfterAdvice",
                }
                is_csharp = any(tail in csharp_tails for tail in matched_advice)
                if is_csharp:
                    recovery_hint = (
                        f"Method '{symbol}' is decorated with a C# AOP attribute "
                        f"({', '.join(matched_advice)}). Callers are wired at runtime by "
                        f"PostSharp / Castle DynamicProxy / a method-boundary aspect framework "
                        f"and have no C# call sites. Search for the aspect registration via "
                        f"code_keyword(queries=['{advice_class or symbol}'], glob='**/*.cs') "
                        f"or look for the framework's interception configuration."
                    )
                else:
                    recovery_hint = (
                        f"Method '{symbol}' is annotated as AOP advice "
                        f"({', '.join(matched_advice)}). Callers are wired at weave time by "
                        f"ByteBuddy/AspectJ and have no Java call sites. "
                        f"Search for the advice registration via "
                        f"code_keyword(queries=['{advice_class or symbol}'], glob='**/*Instrumentation*.java') "
                        f"or via @Aspect pointcut declarations."
                    )
                # Surface as a diagnostic (the AC-3 contract); thread through
                # the final _response call below via a local advice_diagnostics
                # list. Data-field surfacing is retained for back-compat with
                # the test fixtures and downstream consumers.
                advice_diagnostics.append(server_impl._diagnostic(
                    "advice_pattern_detected",
                    recovery_hint,
                    recovery_tools=["code_keyword"],
                    recovery_usage=(
                        f"code_keyword(queries=['{advice_class or symbol}'], "
                        f"glob='**/*Instrumentation*.java')"
                        if not is_csharp else
                        f"code_keyword(queries=['{advice_class or symbol}'], glob='**/*.cs')"
                    ),
                ))

    if context_depth > 0:
        # Gather all immediate caller/callee ids in one pass
        immediate_ids: set[str] = set()
        if direction in {"both", "outgoing"}:
            for edges in (index._out.get(node_id, []),):
                for e in edges:
                    if e.get("relation") != "calls":
                        continue
                    tgt = e.get("target")
                    if isinstance(tgt, str):
                        immediate_ids.add(tgt)
        if direction in {"both", "incoming"}:
            for edges in (index._in.get(node_id, []),):
                for e in edges:
                    if e.get("relation") != "calls":
                        continue
                    src = e.get("source")
                    if isinstance(src, str):
                        immediate_ids.add(src)
        immediate_ids.discard(node_id)
        # Single combined one-hop expansion across all immediate neighbors
        already_known = immediate_ids | {node_id}
        neighborhood = index.one_hop_neighbors(immediate_ids, relations=["calls"])
        context_entries: list[dict[str, Any]] = []
        seen_context: set[str] = set()
        for e in neighborhood.get("edges") or []:
            for other in (e.get("source"), e.get("target")):
                if not isinstance(other, str) or other in already_known or other in seen_context:
                    continue
                n = index.get_node(other) or {}
                c_label, c_id = community_lookup.get(other, (None, None))
                context_entries.append({
                    "id": other,
                    "label": n.get("label", other),
                    "kind": n.get("kind"),
                    "source_file": n.get("source_file"),
                    "community": c_label,
                    "community_id": c_id,
                    "relation": e.get("relation"),
                })
                seen_context.add(other)
        data["context"] = context_entries

    # Wave 1p2q3 (1p2q9 B): per-language attribution-confidence counts.
    data["attribution_counts_by_language"] = server_impl._compute_attribution_counts_by_language(_attr_edges, index)

    # 1p8gy AC-5: active memory attached to the symbol or its defining file.
    _mem_advisories = server_impl._memory_advisories_for_path(
        root, str((index.get_node(node_id) or {}).get("source_file") or file or ""), symbol=symbol,
    )
    if _mem_advisories:
        data["memory_advisories"] = _mem_advisories

    return _attach_auto_rebuild_diag(
        server_impl._response("ok", data, diagnostics=advice_diagnostics, next_tools=["code_read", "code_callgraph"], usage=f"code_callgraph(symbol={symbol!r}, direction='both')"),
        index,
    )

def _match_import_to_target(import_entry: dict[str, Any], target_rel: str, importing_file_rel: str) -> bool:
    """Return True if *import_entry* appears to import *target_rel*."""
    from wf_server import server_impl
    module = import_entry.get("module", "")
    if not module:
        return False

    target_path = Path(target_rel)
    target_stem = target_rel
    for ext in (".py", ".ts", ".js", ".tsx", ".jsx"):
        if target_stem.endswith(ext):
            target_stem = target_stem[: -len(ext)]
            break

    # Heuristic 1: module path normalization
    # Strip leading dots (relative Python imports) then normalize
    stripped = module.lstrip(".")
    normalized = stripped.replace(".", "/")
    if (
        normalized == target_stem
        or target_rel.endswith("/" + normalized + ".py")
        or target_rel.endswith("/" + normalized + ".ts")
        or target_rel.endswith("/" + normalized + ".js")
        or target_rel.endswith("/" + normalized + ".tsx")
        or target_rel.endswith("/" + normalized + ".jsx")
        or target_stem.endswith("/" + normalized)
        or normalized == target_stem.split("/")[-1]
    ):
        return True

    # Heuristic 2: filename stem match (≥ 4 chars)
    module_parts = normalized.replace("/", ".").split(".")
    module_last = module_parts[-1] if module_parts else ""
    target_file_stem = target_path.stem
    if len(module_last) >= 4 and module_last == target_file_stem:
        return True

    # Heuristic 3: relative path resolution for JS/TS ./.. imports
    if module.startswith(("./", "../")):
        importing_dir = Path(importing_file_rel).parent
        try:
            resolved_base = (importing_dir / module).as_posix()
            # Normalize to remove .. components
            resolved_parts = []
            for part in resolved_base.split("/"):
                if part == "..":
                    if resolved_parts:
                        resolved_parts.pop()
                else:
                    resolved_parts.append(part)
            resolved_str = "/".join(resolved_parts)
            # Ensure no escaping
            if resolved_str.startswith(".."):
                pass  # escaped repo, skip
            else:
                candidates = [
                    resolved_str,
                    resolved_str + ".ts",
                    resolved_str + ".tsx",
                    resolved_str + ".js",
                    resolved_str + ".jsx",
                    resolved_str + "/index.ts",
                    resolved_str + "/index.js",
                ]
                if target_rel in candidates:
                    return True
        except Exception:
            pass

    return False

def _code_impact_heuristic_response(root: Path, path: str, max_results: int = 50) -> dict[str, Any]:
    """Find all files that import a given file (reverse dependency analysis).

    Heuristic import detection covers Python, JavaScript, TypeScript, Go, and
    Rust (see ``_IMPORT_PARSERS``). Targets in other languages (Swift, Java,
    Kotlin, C/C++/C#, etc.) return ``unsupported_language: true`` rather than
    silently scanning every file and returning zero importers (wave 130ol).
    For graph-backed impact analysis on supported tree-sitter languages, use
    ``symbol=`` mode instead.
    """
    from wf_server import server_impl
    resolved = server_impl._resolve_repo_path(root, path)
    if resolved is None:
        return server_impl._response(
            "error", {"path": path},
            diagnostics=[server_impl._diagnostic("path_rejected", f"Path '{path}' is outside the project root or invalid.")],
            next_tools=["code_list_files"], usage="code_list_files()",
        )
    if not resolved.exists():
        return server_impl._response(
            "error", {"path": path},
            diagnostics=[server_impl._diagnostic("file_not_found", f"File '{path}' does not exist.")],
            next_tools=["code_list_files"], usage="code_list_files()",
        )

    root_r = root.resolve()
    target_rel = str(resolved.relative_to(root_r)).replace("\\", "/")

    # AC-12: explicit unsupported-language diagnostic. The heuristic only
    # detects imports in Python/JS/TS/Go/Rust; for any other suffix, scanning
    # every file in the repo to return zero importers is wasteful and
    # misleading. Surface the limitation so operators know to use a different
    # tool (or accept that heuristic impact analysis doesn't apply).
    target_suffix = resolved.suffix.lower()
    if target_suffix in server_impl._JS_TS_SUFFIXES:
        target_lang = server_impl._EXT_TO_LANG.get(target_suffix, "javascript")
    else:
        target_lang = server_impl._EXT_TO_LANG.get(target_suffix, "")
    if target_lang not in server_impl._IMPORT_PARSERS:
        supported = sorted(server_impl._IMPORT_PARSERS.keys())
        return server_impl._response(
            "ok",
            {
                "path": target_rel,
                "importers": [],
                "truncated": False,
                "total_found": 0,
                "method": "heuristic",
                "unsupported_language": True,
                "target_language": target_lang or "unknown",
                "supported_languages": supported,
            },
            diagnostics=[server_impl._diagnostic(
                "unsupported_language",
                f"Heuristic code_impact does not parse imports for language '{target_lang or 'unknown'}' "
                f"(supported: {', '.join(supported)}). For graph-backed analysis, query a symbol defined in this file with code_impact(symbol=...).",
                recovery_tools=["code_impact", "code_references"],
                recovery_usage=f"code_impact(symbol='SomeSymbolFromThisFile')",
            )],
            next_tools=["code_impact", "code_references"],
            usage=f"code_impact(symbol='SomeSymbolFromThisFile')  # graph mode",
        )

    importers: list[dict[str, Any]] = []
    total = 0
    limit_hit = max_results + 1

    for p in server_impl._walk_repo_for_navigation(root):
        file_rel = str(p.resolve().relative_to(root_r)).replace("\\", "/")
        if file_rel == target_rel:
            continue
        try:
            source = p.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            continue

        suffix = p.suffix.lower()
        if suffix == ".py":
            lang = "python"
        elif suffix in server_impl._JS_TS_SUFFIXES:
            lang = server_impl._EXT_TO_LANG.get(suffix, "javascript")
        else:
            lang = server_impl._EXT_TO_LANG.get(suffix, "")

        parser_entry = server_impl._IMPORT_PARSERS.get(lang)
        if not parser_entry:
            continue

        parser_fn, _ = parser_entry
        try:
            imports = parser_fn(source)
        except Exception:
            continue

        for imp in imports:
            if _match_import_to_target(imp, target_rel, file_rel):
                total += 1
                if len(importers) < max_results:
                    importers.append({
                        "file": file_rel,
                        "import_statement": imp.get("module", ""),
                        "kind": imp.get("kind", "import"),
                    })
                if total >= limit_hit:
                    break
        if total >= limit_hit:
            break

    # Wave 1p2q3 (1p2q9 Workstream D): heuristic-no-matches diagnostic.
    # When the heuristic import-walk found zero importers for a TS file, the
    # silent empty result is the highest-confusion outcome — operators see
    # `affected: []` and assume the file has no callers, but the more common
    # cause is the heuristic can't resolve aliased imports (e.g. Nx monorepo
    # `@scope/lib` aliases that don't match the file's literal repo path).
    # Surface a diagnostic recommending `symbol=` graph mode or `code_references`.
    diagnostics: list[dict[str, Any]] = []
    if total == 0 and target_lang in ("typescript", "javascript", "tsx", "jsx"):
        diagnostics.append(server_impl._diagnostic(
            "heuristic_import_no_matches",
            f"No importers found for '{target_rel}' via heuristic import-statement walk. "
            f"Common cause on TS/JS monorepos: imports use path aliases (e.g. `@scope/lib`) "
            f"that the heuristic doesn't resolve. For coverage on aliased imports, query a "
            f"specific symbol defined in this file: code_impact(symbol='SomeSymbolFromThisFile'). "
            f"To cross-check via the tree-sitter parser, use code_references(symbol='SomeSymbolFromThisFile').",
            recovery_tools=["code_impact", "code_references"],
            recovery_usage=f"code_impact(symbol='SomeSymbolFromThisFile')",
        ))
    # 1p8gy AC-5: active memory attached to the file whose impact is queried.
    _mem_advisories = server_impl._memory_advisories_for_path(root, target_rel)
    return server_impl._response(
        "ok",
        {
            "path": target_rel,
            "importers": importers,
            "truncated": total > max_results,
            "total_found": total,
            **({"memory_advisories": _mem_advisories} if _mem_advisories else {}),
            "method": "heuristic",
        },
        diagnostics=diagnostics,
        next_tools=["code_read"],
        usage=f"code_read(path='{target_rel}')",
    )

def _suggest_near_communities(
    communities: list[dict[str, Any]], query: str, n: int = 5
) -> list[dict[str, Any]]:
    """Return up to n near-match communities ranked by id/label substring then node count."""
    from wf_server import server_impl
    query_lower = (query or "").strip().lower()
    # Buckets: 0=substring in community_id, 1=substring in label, 2=fallback by size
    buckets: list[list[tuple[int, dict[str, Any]]]] = [[], [], []]
    for c in communities:
        cid = str(c.get("community_id") or "")
        if not cid:
            continue
        label = str(c.get("label") or "")
        node_count = int(c.get("node_count") or 0)
        entry = {"community_id": cid, "label": label, "node_count": node_count}
        if query_lower and query_lower in cid.lower():
            buckets[0].append((-node_count, entry))
        elif query_lower and query_lower in label.lower():
            buckets[1].append((-node_count, entry))
        else:
            buckets[2].append((-node_count, entry))
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for bucket in buckets:
        for _, entry in sorted(bucket, key=lambda x: x[0]):
            cid = entry["community_id"]
            if cid in seen:
                continue
            results.append(entry)
            seen.add(cid)
            if len(results) >= n:
                return results
    return results

def _load_cluster_lookup_with_ids(root: Path, layer: str = "project") -> dict[str, tuple[str, str]]:
    """Return node_id → (community_label, community_id) mapping (wave 130rj).

    Field feedback §1.1: every tool that surfaces a community label
    should also expose the community_id needed to drill in via
    ``code_graph_community``. Returning both eliminates the failed-call
    recovery dance documented in the feedback report.

    Returns an empty dict when the cluster artifact is absent.
    """
    from wf_server import server_impl
    try:
        gc = server_impl._load_script("graph_cluster")
        payload = gc.read_cluster_payload(root, layer)
        if not payload.get("present"):
            return {}
        lookup: dict[str, tuple[str, str]] = {}
        for community in (payload.get("communities") or []):
            label = str(community.get("label") or "")
            community_id = str(community.get("community_id") or "")
            for nid in (community.get("node_ids") or []):
                lookup[str(nid)] = (label, community_id)
        return lookup
    except Exception:
        return {}

def _extract_java_owner_class_from_node_id(node_id: str) -> str | None:
    """Parse owner class name from a Java graph node_id.

    Node IDs have format ``<file>::<symbol>``. For Java the symbol part is
    ``<Class>.<method>`` or ``<Outer>.<Inner>.<method>`` etc. Return the
    simple class name (last `.`-segment before the method), or None when
    the symbol is bare (no class context).
    """
    if not node_id or "::" not in node_id:
        return None
    symbol_part = node_id.rsplit("::", 1)[-1]
    if "." not in symbol_part:
        return None
    # Drop the trailing method name; take the last segment of what remains.
    class_path = symbol_part.rsplit(".", 1)[0]
    return class_path.rsplit(".", 1)[-1] or None

def _resolve_java_receiver_type(invocation_node, source_bytes: bytes) -> str | None:
    from wf_server import server_impl
    return server_impl._load_script("graph_indexer")._resolve_java_receiver_type(invocation_node, source_bytes)

def _annotate_java_call_sites_with_receiver_type(
    path: Path,
    callee_label: str,
    refs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Annotate Java call-site refs with ``_receiver_type`` field.

    Each ref's ``_receiver_type`` is the resolved simple class name of the
    method_invocation's receiver, or None when uncertain (preserve per
    false-positive bias). Refs whose line has no matching method_invocation
    candidate get ``_receiver_type: None``.
    """
    from wf_server import server_impl
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        # Wave 1p3hd: shared cache.
        tree = server_impl._cached_ts_parse(path.resolve(), "java", source)
    except Exception:
        return refs
    if tree is None:
        return refs
    source_bytes = source.encode("utf-8", errors="replace")
    line_to_invocations: dict[int, list] = {}
    stack = [tree.root_node]
    while stack:
        n = stack.pop()
        if getattr(n, "type", "") == "method_invocation":
            name_node = n.child_by_field_name("name")
            if name_node is not None:
                name_text = source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
                if name_text == callee_label:
                    line = n.start_point[0] + 1
                    line_to_invocations.setdefault(line, []).append(n)
        stack.extend(reversed(getattr(n, "children", []) or []))
    for ref in refs:
        line = ref.get("line") or 0
        invocations = line_to_invocations.get(line, [])
        if not invocations:
            ref["_receiver_type"] = None
            continue
        # If multiple invocations on one line, take the first resolvable one.
        resolved: str | None = None
        for inv in invocations:
            r = _resolve_java_receiver_type(inv, source_bytes)
            if r is not None:
                resolved = r
                break
        ref["_receiver_type"] = resolved
    return refs

def _scan_call_sites_in_file(root: Path, callee_label: str, source_file: str) -> list[dict[str, Any]]:
    """Scan source_file for call sites of callee_label. Returns list sorted by line.

    For Java files, each ref carries a ``_receiver_type`` annotation
    (simple class name of the method_invocation's receiver, or None when
    uncertain). Callers use the annotation to filter phantom cross-class
    callers when the queried symbol's owning class is known (wave 130rj —
    130tw).
    """
    from wf_server import server_impl
    p = root / source_file
    if not p.is_file():
        return []
    files = [p]
    restrict = frozenset({source_file})
    if source_file.endswith(".py"):
        refs = server_impl._python_reference_call_sites(root, callee_label, restrict_files=restrict, _files=files)
    else:
        ts_refs = server_impl._treesitter_references(root, callee_label, restrict_files=restrict, _files=files)
        refs = [r for r in ts_refs if r.get("reference_kind") == "call_sites"]
        if not refs:
            text_refs = server_impl._non_python_references(root, callee_label, restrict_files=restrict, _files=files)
            refs = [r for r in text_refs if r.get("reference_kind") == "call_sites"]
        if source_file.endswith(".java") and refs:
            refs = _annotate_java_call_sites_with_receiver_type(p, callee_label, refs)
    return sorted(refs, key=lambda r: r.get("line") or 0)

def _scan_all_call_sites_in_file(
    root: Path, callee_labels: list[str], source_file: str
) -> dict[str, list[dict[str, Any]]]:
    """Scan source_file once for all callee_labels. Returns dict: label → sorted call sites."""
    from wf_server import server_impl
    if not callee_labels:
        return {}
    p = root / source_file
    result: dict[str, list[dict[str, Any]]] = {label: [] for label in callee_labels}
    if not p.is_file():
        return result
    label_set = set(callee_labels)
    if source_file.endswith(".py"):
        import ast as _ast
        try:
            source = p.read_text(encoding="utf-8", errors="replace")
            tree = _ast.parse(source, filename=str(p))
        except (SyntaxError, OSError):
            return result
        lines = source.splitlines()
        for node in _ast.walk(tree):
            if not isinstance(node, _ast.Call):
                continue
            func = node.func
            matched_label: str | None = None
            if isinstance(func, _ast.Name) and func.id in label_set:
                matched_label = func.id
            elif isinstance(func, _ast.Attribute) and func.attr in label_set:
                matched_label = func.attr
            if matched_label is None:
                continue
            line = getattr(node, "lineno", 0)
            if line <= 0 or line > len(lines):
                continue
            result[matched_label].append({
                "path": source_file,
                "line": line,
                "snippet": lines[line - 1].rstrip(),
                "language": "python",
                "method": "ast",
                "reference_kind": "call_sites",
            })
        for label in result:
            result[label].sort(key=lambda r: r.get("line") or 0)
    else:
        files = [p]
        restrict = frozenset({source_file})
        for label in callee_labels:
            ts_refs = server_impl._treesitter_references(root, label, restrict_files=restrict, _files=files)
            refs = [r for r in ts_refs if r.get("reference_kind") == "call_sites"]
            if not refs:
                text_refs = server_impl._non_python_references(root, label, restrict_files=restrict, _files=files)
                refs = [r for r in text_refs if r.get("reference_kind") == "call_sites"]
            result[label] = sorted(refs, key=lambda r: r.get("line") or 0)
    return result

def _first_call_site_at_or_after(call_sites: list[dict[str, Any]], start_line: int) -> dict[str, Any] | None:
    """Return first call site at or after start_line, or None if none found."""
    for ref in call_sites:
        if (ref.get("line") or 0) >= start_line:
            return ref
    return None

def _graph_refresh_and_resolve(
    root: Path,
    symbol: str,
    layer: str = "project",
) -> tuple[Any, Optional[str]]:
    """Refresh graph, reload index, resolve symbol — convenience for resolve-symbol callers.

    Returns ``(fresh_index, node_id)`` on success or ``(None, None)`` on refresh
    failure or symbol-still-missing. The caller should swap its existing ``index``
    for ``fresh_index`` so subsequent traversal sees the new graph state (the
    original ``index`` is a stale snapshot).

    Note: returns ``(None, None)`` even when the refresh succeeded but the specific
    symbol still doesn't resolve — callers that need the fresh index for *other*
    symbols (e.g. ``code_graph_path`` with two symbols) should use
    ``_graph_refresh_then_recheck`` directly with a recheck closure that returns
    everything they need to reuse.
    """
    from wf_server import server_impl
    try:
        server_impl.index_build_response(root, content="graph", mode="update")
    except Exception as exc:
        server_impl._wf_log(f"[wavefoundry] graph refresh failed during resolve: {exc!r}")
        return None, None
    try:
        gq = server_impl._load_graph_query()
        # Known rewrite: drop the cached index so the re-read reloads even on
        # a same-(mtime_ns, size) rewrite (coarse-mtime filesystems).
        try:
            gq.invalidate_query_index_cache(root)
        except Exception:
            pass
        new_index = gq.get_query_index(root, layer=layer)
    except Exception as exc:
        server_impl._wf_log(f"[wavefoundry] graph index reload failed after refresh: {exc!r}")
        return None, None
    node_id = new_index.resolve_symbol(symbol)
    if node_id is None:
        return None, None
    return new_index, node_id

def _code_impact_graph_response(
    root: Path,
    symbol: str,
    *,
    max_hops: int = 3,
    layer: str = "project",
    relations: Optional[list[str]] = None,
    max_results: int = 50,
    include_tests: bool = False,
) -> dict[str, Any]:
    # Wave 1p4eq (1p4es hardening): clamp negative max_results to 0. A negative
    # value would otherwise hit Python's drop-last-N slice semantics
    # (`edges[:-1]` returns all-but-one) rather than an empty/capped result.
    from wf_server import server_impl
    max_results = max(0, max_results)
    gq = server_impl._load_graph_query()
    try:
        layer_value = server_impl._graph_layer_value(layer)
    except ValueError as exc:
        return server_impl._response(
            "error",
            {"symbol": symbol, "method": "graph"},
            diagnostics=[server_impl._diagnostic("invalid_arguments", str(exc))],
            next_tools=["wf_help"],
            usage="code_impact(symbol='path::symbol', layer='project')",
        )
    index = gq.get_query_index(root, layer=layer_value)
    if not index.present:
        return server_impl._response(
            "error",
            {"symbol": symbol, "method": "graph", "layer": layer_value},
            **_graph_unavailable_fields(gq, layer_value, index),
        )
    impact = index.graph_impact(symbol, max_hops=max(1, max_hops), relations=relations)
    if not impact.get("resolved"):
        # Wave 1304x / 1304r: refresh-then-resolve before emitting suggestions
        new_index, refreshed_id = _graph_refresh_and_resolve(root, symbol, layer=layer_value)
        if refreshed_id is not None:
            index = new_index
            impact = index.graph_impact(symbol, max_hops=max(1, max_hops), relations=relations)
    if not impact.get("resolved"):
        # Wave 1sbfi (1sbfh): a simple name matching MULTIPLE distinct external
        # supertype ids stays unresolved by design (never silently merged) —
        # surface the grouped breakdown so the caller can re-query with the
        # exact ``external::`` id (council amendment: distinct-id grouping).
        ext_groups = []
        try:
            ext_groups = index.external_supertype_group(symbol)
        except AttributeError:
            pass  # older loaded index module without the helper
        if len(ext_groups) > 1:
            return server_impl._response(
                "ok",
                {
                    "symbol": symbol,
                    "resolved": False,
                    "method": "graph",
                    "layer": layer_value,
                    "external_candidates": ext_groups,
                },
                diagnostics=[server_impl._diagnostic(
                    "external_supertype_ambiguous",
                    f"'{symbol}' matches {len(ext_groups)} distinct external supertypes "
                    f"(declared with different qualifications). Re-query with the exact id, "
                    f"e.g. code_impact(symbol={ext_groups[0]['id']!r}).",
                )],
                next_tools=["code_impact"],
                usage=f"code_impact(symbol={ext_groups[0]['id']!r}, max_hops=2)",
            )
        suggestions = server_impl._suggest_near_symbols(index, symbol)
        return server_impl._response(
            "error",
            {"symbol": symbol, "method": "graph", "layer": layer_value, "suggestions": suggestions},
            diagnostics=[server_impl._diagnostic(
                "graph_symbol_not_found",
                f"Symbol '{symbol}' does not resolve to a graph node (refresh attempted).",
                recovery_tools=["code_definition", "code_keyword"],
                recovery_usage=f"code_definition(symbol_or_path_position={symbol!r})",
            )],
            next_tools=["code_definition"],
            usage=f"code_definition(symbol_or_path_position={symbol!r})",
        )
    community_lookup = _load_cluster_lookup_with_ids(root, layer_value)
    affected_raw = impact.get("affected") or []
    if not include_tests:
        affected_raw = [a for a in affected_raw if not server_impl._is_test_path(str(a.get("source_file") or ""))]
    # Attach community label + id to each affected node (wave 130rj — community label
    # and id dual return per field feedback §1.1).
    def _with_community(a: dict) -> dict:
        c_label, c_id = community_lookup.get(a.get("node_id", ""), (None, None))
        return {**a, "community": c_label, "community_id": c_id}
    affected_enriched = [_with_community(a) for a in affected_raw]
    truncated = len(affected_enriched) > max_results
    # Recompute affected_files after test filter
    affected_files = sorted({str(a.get("source_file") or "") for a in affected_enriched if a.get("source_file")})
    impact_edges = impact.get("edges") or []
    # Wave 1p4es: bound the edges array by max_results. On a high-fan-in symbol
    # (field report: rethrowError, 754 edges) the UNBOUNDED array blew the
    # MCP token cap (~227K chars) even though max_results capped `affected` — the
    # edges list was the size driver. The full list still feeds the attribution
    # counts (accurate); the response carries at most max_results edges plus
    # edges_total so the caller knows the real count (re-query with a higher
    # max_results, or use code_callgraph for the full edge set).
    edges_total = len(impact_edges)
    edges_truncated = edges_total > max_results
    response_edges = impact_edges[:max_results]
    # Wave 1sbfi (1sbfh): external-supertype visibility. When the resolved
    # seed IS an external supertype (blast radius = its project implementors/
    # subtypes + their dependents), label it so consumers never mistake it
    # for a project node. On any seed, surface the node's declared supertypes
    # (project + external, with always-on external counts) — a class whose
    # only supertypes are external no longer reads as "no edges".
    _resolved_id = str(impact.get("node_id") or "")
    _extra: dict[str, Any] = {}
    if _resolved_id.startswith("external::"):
        _extra["external_target"] = True
        _extra["external_name"] = _resolved_id[len("external::"):]
    try:
        _supers = index.supertype_summary(_resolved_id)
    except AttributeError:
        _supers = None
    if _supers:
        _extra["supertypes"] = _supers
    # 1p8gy AC-5: active memory attached to the impacted symbol/file.
    _mem_advisories = server_impl._memory_advisories_for_path(
        root, _resolved_id.split("::", 1)[0] if "::" in _resolved_id else "", symbol=symbol,
    )
    if _mem_advisories:
        _extra["memory_advisories"] = _mem_advisories
    # Wave 1vbuu (1vbut): an empty test-caller set under include_tests=true is
    # NOT evidence of absent test coverage. Two invisibility classes make it a
    # silent empty: (a) test trees the index excludes at build time (this
    # repository's own .wavefoundry/framework/scripts/tests/ is never indexed),
    # and (b) mock- or fixture-driven coverage (patch.object on a parent) that
    # produces no `calls` edge to the symbol. Say so, advisory-only, exactly in
    # the zero-test-affected state; a real test-path hit suppresses it and
    # include_tests=false is untouched.
    _diags: list[dict[str, Any]] = []
    if include_tests and not any(
        server_impl._is_test_path(str(a.get("source_file") or "")) for a in affected_enriched
    ):
        _diags.append(server_impl._diagnostic(
            "test_callers_not_visible",
            "include_tests=true found no test-path callers, but an empty result does not prove "
            "absent test coverage: test trees excluded from the index at build time carry no "
            "nodes, and mock- or fixture-driven coverage (e.g. patch.object on a caller) produces "
            "no `calls` edge. Corroborate with code_keyword over the test tree for the symbol name "
            "before treating this symbol as untested.",
            recovery_tools=["code_keyword"],
            recovery_usage=f"code_keyword(query={symbol.rsplit('::', 1)[-1]!r}, glob='**/test*')",
            advisory=True,
        ))
    return _attach_auto_rebuild_diag(
        server_impl._response(
            "ok",
            {
                "symbol": symbol,
                # Wave 1p4es: documented response field that was never emitted →
                # came back null (field report). At the OK path the symbol is resolved.
                "resolved": True,
                "node_id": impact.get("node_id"),
                **_extra,
                "layer": layer_value,
                "method": "graph",
                "max_hops": max_hops,
                "relations": impact.get("relations") or [],
                "include_tests": include_tests,
                "affected": affected_enriched[:max_results],
                "affected_files": affected_files,
                "edges": response_edges,
                "edges_total": edges_total,
                "truncated": truncated or edges_truncated,
                "total_found": len(affected_enriched),
                # Wave 1p2q3 (1p2q9 B): per-language attribution-confidence counts.
                "attribution_counts_by_language": server_impl._compute_attribution_counts_by_language(impact_edges, index),
            },
            diagnostics=_diags or None,
            next_tools=["code_callgraph", "code_read"],
            usage=f"code_callgraph(symbol={symbol!r}, direction='both')",
        ),
        index,
    )

def code_impact_response(
    root: Path,
    path: str = "",
    max_results: int = 50,
    *,
    symbol: str = "",
    max_hops: int = 3,
    layer: str = "project",
    relations: Optional[list[str]] = None,
    include_tests: bool = False,
) -> dict[str, Any]:
    """Reverse dependency / impact analysis — heuristic (path) or graph-backed (symbol)."""
    from wf_server import server_impl
    if symbol.strip():
        return _code_impact_graph_response(
            root,
            symbol.strip(),
            max_hops=max_hops,
            layer=layer,
            relations=relations,
            max_results=max_results,
            include_tests=include_tests,
        )
    if not path.strip():
        return server_impl._response(
            "error",
            {"path": path, "symbol": symbol},
            diagnostics=[server_impl._diagnostic("invalid_arguments", "Provide path= for heuristic mode or symbol= for graph mode.")],
            next_tools=["code_impact"],
            usage="code_impact(path='src/module.py')",
        )
    return _code_impact_heuristic_response(root, path, max_results)

def code_risk_score_response(
    root: Path,
    scope: str = "",
    *,
    top: int = 20,
    max_hops: int = 3,
    candidate_cap: int = 200,
    layer: str = "project",
    include_tests: bool = False,
) -> dict[str, Any]:
    """Rank in-scope symbols by composite change-risk (blast-radius × degree) — wave 1p41o."""
    from wf_server import server_impl
    if not scope.strip():
        return server_impl._response(
            "error",
            {"scope": scope},
            diagnostics=[server_impl._diagnostic("invalid_arguments", "Provide scope= (a file path, directory prefix, or glob) to rank.")],
            next_tools=["code_risk_score"],
            usage="code_risk_score(scope='src/module.py')",
        )
    gq = server_impl._load_graph_query()
    try:
        layer_value = server_impl._graph_layer_value(layer)
    except ValueError as exc:
        return server_impl._response(
            "error",
            {"scope": scope},
            diagnostics=[server_impl._diagnostic("invalid_arguments", str(exc))],
            next_tools=["wf_help"],
            usage="code_risk_score(scope='src/', layer='project')",
        )
    index = gq.get_query_index(root, layer=layer_value)
    if not index.present:
        return server_impl._response(
            "error",
            {"scope": scope, "layer": layer_value},
            **_graph_unavailable_fields(gq, layer_value, index),
        )
    result = index.risk_score(
        scope.strip(),
        max_hops=max(1, max_hops),
        top=top,
        candidate_cap=candidate_cap,
        is_test_path=None if include_tests else server_impl._is_test_path,
    )
    if result.get("over_candidate_cap"):
        return server_impl._response(
            "error",
            {**result, "include_tests": include_tests},
            diagnostics=[server_impl._diagnostic(
                "scope_too_large",
                f"{result.get('candidate_count')} candidate symbols in scope exceeds the cap "
                f"({result.get('candidate_cap')}); narrow scope= to a file or subdirectory so the "
                f"per-symbol blast-radius BFS stays bounded.",
            )],
            next_tools=["code_risk_score", "code_list_files"],
            usage="code_risk_score(scope='src/submodule/')",
        )
    next_tools = ["code_impact", "code_read"] if result.get("results") else ["code_list_files", "code_outline"]
    return _attach_auto_rebuild_diag(
        server_impl._response(
            "ok",
            {**result, "layer": layer_value, "include_tests": include_tests},
            next_tools=next_tools,
            usage="code_impact(symbol='path::symbol') to size a single symbol's blast radius",
        ),
        index,
    )

def code_callgraph_response(
    root: Path,
    symbol: str,
    *,
    depth: int = 1,
    direction: str = "both",
    layer: str = "project",
    include_tests: bool = False,
) -> dict[str, Any]:
    from wf_server import server_impl
    gq = server_impl._load_graph_query()
    try:
        layer_value = server_impl._graph_layer_value(layer)
    except ValueError as exc:
        return server_impl._response(
            "error",
            {"symbol": symbol},
            diagnostics=[server_impl._diagnostic("invalid_arguments", str(exc))],
            next_tools=["wf_help"],
            usage="code_callgraph(symbol='path::symbol')",
        )
    direction_value = (direction or "both").strip().lower()
    if direction_value not in ("callers", "callees", "both"):
        return server_impl._response(
            "error",
            {"symbol": symbol, "direction": direction},
            diagnostics=[server_impl._diagnostic("invalid_arguments", "direction must be callers, callees, or both.")],
            next_tools=["code_callgraph"],
            usage="code_callgraph(symbol='path::symbol', direction='both')",
        )
    index = gq.get_query_index(root, layer=layer_value)
    if not index.present:
        return server_impl._response(
            "error",
            {"symbol": symbol, "layer": layer_value},
            **_graph_unavailable_fields(gq, layer_value, index),
        )
    result = index.callgraph(symbol, depth=max(1, depth), direction=direction_value)  # type: ignore[arg-type]
    if not result.get("resolved"):
        # Wave 1304x / 1304r: refresh-then-resolve before emitting suggestions
        new_index, refreshed_id = _graph_refresh_and_resolve(root, symbol, layer=layer_value)
        if refreshed_id is not None:
            index = new_index
            result = index.callgraph(symbol, depth=max(1, depth), direction=direction_value)  # type: ignore[arg-type]
    if not result.get("resolved"):
        suggestions = server_impl._suggest_near_symbols(index, symbol)
        return server_impl._response(
            "error",
            {"symbol": symbol, "layer": layer_value, "suggestions": suggestions},
            diagnostics=[server_impl._diagnostic(
                "graph_symbol_not_found",
                f"Symbol '{symbol}' does not resolve to a graph node (refresh attempted).",
                recovery_tools=["code_definition", "code_keyword"],
                recovery_usage=f"code_definition(symbol_or_path_position={symbol!r})",
            )],
            next_tools=["code_definition"],
            usage=f"code_definition(symbol_or_path_position={symbol!r})",
        )

    if not include_tests:
        nodes_kept = [
            n for n in (result.get("nodes") or [])
            if not server_impl._is_test_path(str(n.get("source_file") or ""))
        ]
        kept_ids = {n.get("id") for n in nodes_kept if n.get("id")}
        edges_kept = [
            e for e in (result.get("edges") or [])
            if e.get("source") in kept_ids and e.get("target") in kept_ids
        ]
        result["nodes"] = nodes_kept
        result["edges"] = edges_kept

    # Enrich call edges with call-site line numbers via targeted file scan
    _node_map: dict[str, dict[str, Any]] = {
        n["id"]: n for n in (result.get("nodes") or []) if isinstance(n.get("id"), str)
    }
    # Pre-collect all (src_file → callee_labels) and batch-scan each file once
    _file_callees: dict[str, set[str]] = {}
    for edge in (result.get("edges") or []):
        if edge.get("relation") != "calls":
            continue
        src_id = str(edge.get("source") or "")
        tgt_id = str(edge.get("target") or "")
        if src_id.startswith("external::"):
            continue
        src_node = _node_map.get(src_id) or {}
        tgt_node = _node_map.get(tgt_id) or {}
        src_file = src_node.get("source_file") or (src_id.split("::")[0] if "::" in src_id else "")
        callee_label = tgt_node.get("label") or (tgt_id.rsplit("::", 1)[-1] if "::" in tgt_id else tgt_id)
        if src_file and callee_label:
            _file_callees.setdefault(src_file, set()).add(callee_label)
    _batch_sites: dict[str, dict[str, list[dict[str, Any]]]] = {
        src_file: _scan_all_call_sites_in_file(root, list(labels), src_file)
        for src_file, labels in _file_callees.items()
    }
    enriched_edges: list[dict[str, Any]] = []
    for edge in (result.get("edges") or []):
        new_edge = dict(edge)
        if edge.get("relation") == "calls":
            src_id = str(edge.get("source") or "")
            tgt_id = str(edge.get("target") or "")
            if not src_id.startswith("external::"):
                src_node = _node_map.get(src_id) or {}
                tgt_node = _node_map.get(tgt_id) or {}
                src_file = src_node.get("source_file") or (src_id.split("::")[0] if "::" in src_id else "")
                callee_label = tgt_node.get("label") or (tgt_id.rsplit("::", 1)[-1] if "::" in tgt_id else tgt_id)
                if src_file and callee_label:
                    sites = _batch_sites.get(src_file, {}).get(callee_label, [])
                    src_loc = src_node.get("source_location") or "0:0"
                    try:
                        src_start = int(str(src_loc).split(":")[0])
                    except (ValueError, IndexError):
                        src_start = 0
                    ref = _first_call_site_at_or_after(sites, src_start)
                    if ref:
                        new_edge["line"] = ref["line"]
        enriched_edges.append(new_edge)

    return _attach_auto_rebuild_diag(
        server_impl._response(
            "ok",
            {
                "symbol": symbol,
                "node_id": result.get("node_id"),
                "layer": layer_value,
                "depth": depth,
                "direction": direction_value,
                "include_tests": include_tests,
                "nodes": result.get("nodes") or [],
                "edges": enriched_edges,
            },
            next_tools=["code_impact", "code_read"],
            usage=f"code_impact(symbol={symbol!r}, max_hops=2)",
        ),
        index,
    )

class _BetweennessUnsupportedForCollapsedView(Exception):
    """Wave 1wpaj: betweenness was requested alongside a collapse flag.

    Raised inside the betweenness serve block so the existing handler performs
    the same teardown it does for any other refusal (empty rows, no method, no
    metadata). The skip reason and note for this case are set BEFORE the block
    and are deliberately not overwritten afterwards.
    """

def wf_graph_report_response(
    root: Path,
    *,
    layer: str = "project",
    limit: int = 20,
    sections: Optional[list[str]] = None,
    exclude_generated: bool = False,
    exclude_external: bool = False,
    collapse_generated_files: bool = False,
    collapse_class_module_pairs: bool = False,
    collapse_package_to_directory: bool = False,
) -> dict[str, Any]:
    # Wave 1xny6: this response reads the graph, the communities and the
    # persisted betweenness — three reads that must describe ONE build. The pin
    # binds them to a single generation for the whole response; a publication
    # landing mid-report rebinds the NEXT call, not this one.
    from wf_server import server_impl
    with server_impl._graph_snapshot_module().pinned(root, "project"):
        return _wf_graph_report_response_pinned(
            root, layer=layer, limit=limit, sections=sections,
            exclude_generated=exclude_generated, exclude_external=exclude_external,
            collapse_generated_files=collapse_generated_files,
            collapse_class_module_pairs=collapse_class_module_pairs,
            collapse_package_to_directory=collapse_package_to_directory,
        )

def _wf_graph_report_response_pinned(
    root: Path,
    *,
    layer: str = "project",
    limit: int = 20,
    sections: Optional[list[str]] = None,
    exclude_generated: bool = False,
    exclude_external: bool = False,
    collapse_generated_files: bool = False,
    collapse_class_module_pairs: bool = False,
    collapse_package_to_directory: bool = False,
) -> dict[str, Any]:
    from wf_server import server_impl
    gq = server_impl._load_graph_query()
    try:
        layer_value = server_impl._graph_layer_value(layer)
    except ValueError as exc:
        return server_impl._response(
            "error",
            {"layer": layer},
            diagnostics=[server_impl._diagnostic("invalid_arguments", str(exc))],
            next_tools=["wf_help"],
            usage="wf_graph_report(layer='project')",
        )
    index = gq.get_query_index(root, layer=layer_value)
    if not index.present and not isinstance(getattr(index, "diagnostic", None), dict):
        # Only true absence may trigger a rebuild; failures require their own recovery.
        # Wave 1304x / 1304r: refresh-then-recheck on absent graph
        def _recheck_present():
            new_index = gq.get_query_index(root, layer=layer_value)
            return new_index if new_index.present else None
        refreshed_index = server_impl._graph_refresh_then_recheck(root, _recheck_present)
        if refreshed_index is not None:
            index = refreshed_index
    if not index.present:
        return server_impl._response(
            "error",
            {"layer": layer_value},
            **_graph_unavailable_fields(gq, layer_value, index),
        )
    # Wave 130rj (130su): collapse_generated_files aggregates each generated
    # file into a single file-node before running the report. Drops internal
    # generated edges and rewrites boundary edges. The collapse runs on a
    # snapshot payload; the original index is not mutated. Per-symbol tools
    # (code_callhierarchy/code_impact/code_graph_path/code_callgraph) deliberately
    # do NOT support this flag — they need the full per-symbol view.
    if collapse_generated_files:
        original_payload = {
            "layer": index.layer,
            "present": index.present,
            "nodes": list(index.nodes),
            "edges": list(index.edges),
        }
        collapsed_payload = gq.collapse_generated_view(original_payload)
        index = gq.GraphQueryIndex(collapsed_payload)
    # Wave 13129 (1312h): collapse_class_module_pairs merges Swift file+class
    # pairs into one node for report consumption. Independent of generated-file
    # collapse — both can be applied together. Swift-first; other languages
    # extend via _CLASS_MODULE_COLLAPSE_LANGUAGES table in graph_query.py.
    if collapse_class_module_pairs:
        original_payload = {
            "layer": index.layer,
            "present": index.present,
            "nodes": list(index.nodes),
            "edges": list(index.edges),
        }
        merged_payload = gq.collapse_class_module_view(original_payload)
        index = gq.GraphQueryIndex(merged_payload)
    # Wave 131bt (1319m): collapse_package_to_directory aggregates files in a
    # directory into a single package/namespace node per language detection
    # (Go: matching package declarations; Python: __init__.py presence;
    # Java/Kotlin/Scala/C#/PHP: matching package/namespace declarations;
    # Swift: directory-presence convention). Independent of class/module
    # pair collapse — both can apply together. Per-symbol tools don't consume.
    if collapse_package_to_directory:
        original_payload = {
            "layer": index.layer,
            "present": index.present,
            "nodes": list(index.nodes),
            "edges": list(index.edges),
        }
        directory_payload = gq.collapse_package_to_directory_view(original_payload, root=root)
        index = gq.GraphQueryIndex(directory_payload)
    # Wave 130rj — field feedback §6.4 + §6.2: generated-node eligibility.
    # Wave 1wpaj: hoisted above the report call so eligibility can be applied
    # BEFORE top-N truncation rather than after it.
    def _node_is_generated(nid: str) -> bool:
        n = index.get_node(nid) or {}
        return bool(n.get("generated"))

    def _report_eligible(nid: str) -> bool:
        """Wave 1wpaj: the filter-before-truncation predicate.

        Both public flags resolve to one predicate handed to `report()`, which
        applies it at each of its three truncation sites. Filtering used to run
        on the already-sliced rows, so a filtered request silently returned
        fewer rows than asked for; at limit=1 with external nodes ranked on top,
        it returned nothing at all.
        """
        if exclude_external and nid.startswith("external::"):
            return False
        if exclude_generated and _node_is_generated(nid):
            return False
        return True

    _eligible = _report_eligible if (exclude_external or exclude_generated) else None
    report = index.report(
        limit=max(1, min(limit, 100)), sections=sections, eligible=_eligible,
        # Wave 1wpie: the partition predicate. Passed unconditionally, including
        # under `exclude_generated`, because that filter must not erase
        # Evidence/Data -- the two are orthogonal classifications.
        is_evidence=index.is_evidence_node,
    )
    # AC-from-wave-130rj (field feedback §2.2): community overview section.
    # Adds a single-call architectural-orientation surface listing top
    # communities by node_count with the IDs needed to follow up via
    # code_graph_community. Lazy-loaded so the section only fires when
    # requested OR when the default section set is used.
    wanted = set(sections) if sections is not None else {"fan_in", "fan_out", "orphan_docs", "chokepoints", "file_hubs", "communities"}
    # Wave 1wpie delivery review (ARCH-DEL-3): degradation on the evidence
    # partition must reach the caller, not be swallowed.
    partition_diagnostics: list[dict[str, Any]] = []
    if "communities" in wanted:
        try:
            gc = server_impl._load_script("graph_cluster")
            cluster_layer = layer_value
            payload = gc.read_cluster_payload(root, cluster_layer)
            communities_section: list[dict[str, Any]] = []
            # Wave 1wpie delivery council: `evidence_ranked` and `degree` are
            # bound INSIDE the `present` branch but read after it, so a tree
            # with a graph and no cluster artifact -- an ordinary fresh target
            # repository -- raised UnboundLocalError and was reported as
            # "the partition failed and does not describe the graph". That is
            # the third indistinguishable state the diagnostic below argues is
            # worse than the ambiguity it replaced. An absent cluster payload
            # means there are simply no communities; say that by serving two
            # empty arrays and no false alarm.
            evidence_ranked: list[dict[str, Any]] = []
            degree: dict[str, int] = {}
            if payload.get("present"):
                # Build degree lookup for hub selection.
                for nid, edges in index._in.items():
                    degree[nid] = degree.get(nid, 0) + len(edges)
                for nid, edges in index._out.items():
                    degree[nid] = degree.get(nid, 0) + len(edges)
                # Wave 1wpaj: eligibility BEFORE truncation here too. This
                # section is artifact-defined rather than a `report()` section,
                # so it needs its own filter-first pass; leaving it post-sliced
                # reproduced the wave's headline defect exactly (a filtered
                # limit=1 request returning [] while an eligible community sat
                # one row below a generated-dominated one).
                _all_communities = payload.get("communities") or []
                if exclude_generated:
                    _all_communities = [
                        c for c in _all_communities
                        if float(c.get("generated_node_fraction") or 0.0) <= 0.4
                    ]
                # Wave 1wpie requirement 8: partition BEFORE the top-N slice,
                # and slice each half independently. The majority rule lives in
                # `graph_query` so the community catalog resource applies the
                # SAME rule; two copies would present one community two ways
                # depending on which surface a reader opened. This is the
                # section the wave exists for: on this repository the
                # third-largest community is 987 nodes of one test freeze.
                _gq = server_impl._load_graph_query()
                _majority = _gq.EVIDENCE_COMMUNITY_MAJORITY
                _cap = max(1, min(limit, 100))
                _evidence_shares = {
                    str(c.get("community_id") or ""): _gq.community_evidence_share(index, c)
                    for c in _all_communities
                }
                _production = [c for c in _all_communities
                               if _evidence_shares.get(str(c.get("community_id") or ""), 0.0) <= _majority]
                _evidence = [c for c in _all_communities
                             if _evidence_shares.get(str(c.get("community_id") or ""), 0.0) > _majority]
                ranked = sorted(
                    _production,
                    key=lambda c: -int(c.get("node_count") or 0),
                )[:_cap]
                evidence_ranked = sorted(
                    _evidence,
                    key=lambda c: -int(c.get("node_count") or 0),
                )[:_cap]
                for c in ranked:
                    cid = str(c.get("community_id") or "")
                    label = str(c.get("label") or cid)
                    members = c.get("node_ids") or []
                    hub_id = max(members, key=lambda n: degree.get(n, 0), default="") if members else ""
                    hub_label = (index.get_node(hub_id) or {}).get("label", hub_id) if hub_id else ""
                    # Wave 130rj — field feedback §6.5: per-community generated_node_fraction
                    # comes from the cluster artifact; flag generated-dominated
                    # communities (>40%) so agents can decide whether to trust the
                    # community's structural metrics.
                    gen_fraction = float(c.get("generated_node_fraction") or 0.0)
                    entry = {
                        "community_id": cid,
                        "label": label,
                        "node_count": int(c.get("node_count") or 0),
                        "hub_node_id": hub_id,
                        "hub_label": hub_label,
                        "generated_node_fraction": gen_fraction,
                    }
                    if gen_fraction > 0.4:
                        entry["community_type"] = "generated-dominated"
                    communities_section.append(entry)
            # Wave 130rj — exclude_generated suppresses generated-dominated
            # communities. Wave 1wpaj moved that filter above the truncation, so
            # nothing remains to strip here; a post-filter would be a no-op on an
            # already-eligible list and would reintroduce the shrink-after-slice
            # shape this wave removed.
            report["communities"] = communities_section
            # The exact parallel Evidence/Data array. Same compatibility fields
            # as a production entry, plus the typed marks requirement 7 names.
            evidence_communities: list[dict[str, Any]] = []
            for c in evidence_ranked:
                cid = str(c.get("community_id") or "")
                members = c.get("node_ids") or []
                hub_id = max(members, key=lambda n: degree.get(n, 0), default="") if members else ""
                reasons: list[str] = []
                for member in members:
                    reasons = index.evidence_reasons(str(member))
                    if reasons:
                        break
                evidence_communities.append({
                    "community_id": cid,
                    "label": str(c.get("label") or cid),
                    "node_count": int(c.get("node_count") or 0),
                    "hub_node_id": hub_id,
                    "hub_label": (index.get_node(hub_id) or {}).get("label", hub_id) if hub_id else "",
                    "generated_node_fraction": float(c.get("generated_node_fraction") or 0.0),
                    "community_type": "evidence_data",
                    "evidence_type": "evidence_data",
                    "evidence_node_share": round(
                        _evidence_shares.get(cid, 0.0), 4),
                    "classification_reasons": reasons or [
                        "majority of community members belong to classified "
                        "machine-result artifacts"],
                })
            report["evidence_communities"] = evidence_communities
        except Exception as exc:  # noqa: BLE001
            # Wave 1wpie delivery review (ARCH-DEL-3): this handler's blast
            # radius now covers the whole evidence partition, so a silent
            # degrade would make an empty `evidence_communities` mean any of
            # three things -- nothing qualified, the build predates the
            # partition, or the partition RAISED. The contract promises a
            # consumer never has to separate the first two; a third
            # indistinguishable state is worse. Report it.
            report.setdefault("communities", [])
            report.setdefault("evidence_communities", [])
            partition_diagnostics.append(server_impl._diagnostic(
                "evidence_partition_degraded",
                "The community/evidence partition failed and both arrays were "
                f"served empty; they do not describe the graph. Cause: {exc}. "
                "Rebuild the graph index, then retry.",
                recovery_tools=["index_build", "index_health"],
                recovery_usage="index_build(content='graph', mode='rebuild')",
            ))

    # Wave 1p9q3 (1p9q1): the betweenness section is SERVED from the persisted
    # build-time ranking in the clusters artifact (graph_cluster.compute_betweenness_ranking:
    # size-tiered exact / igraph-cutoff / degree_fallback, top-200 with method
    # metadata) — never computed at query time. The old inline igraph computation
    # and its 10k-node cap diagnostic are retired; `betweenness_method` +
    # `betweenness_metadata` surface how the persisted ranking was produced.
    if "betweenness" in wanted:
        bw_rows_served: list[dict[str, Any]] = []
        bw_computed = False
        # Wave 1wpaj: betweenness is supported ONLY on the base topology.
        # The persisted centrality order describes the base graph, while every
        # collapse flag rewrites nodes or edges before the report is computed,
        # so serving that order under collapse would label base centrality as
        # collapsed-graph centrality. Refuse explicitly rather than serve a
        # stale order. This also removes a presentation regression the refill
        # would otherwise hit: compact complete-order rows resolve `label` and
        # `kind` through the live index, and under collapse the base node id no
        # longer exists there, so those fields degraded to the raw id and None.
        _collapse_active = (
            collapse_generated_files
            or collapse_class_module_pairs
            or collapse_package_to_directory
        )
        if _collapse_active:
            report["betweenness"] = []
            report["betweenness_computed"] = False
            report["betweenness_skipped_reason"] = "unsupported_for_collapsed_view"
            report["betweenness_note"] = (
                "Betweenness is computed at build time over the BASE graph topology and "
                "persisted in the clusters artifact. Collapse flags rewrite nodes or edges "
                "before the report is computed, so the persisted order does not describe "
                "the collapsed graph and is not served for it. Request betweenness with all "
                "collapse flags false, or read the other sections under collapse."
            )
        try:
            if _collapse_active:
                raise _BetweennessUnsupportedForCollapsedView()
            gc_bw = server_impl._load_script("graph_cluster")
            bw_payload = gc_bw.read_cluster_payload(root, layer_value)
            bw_section = bw_payload.get("betweenness") if bw_payload.get("present") else None
            # Wave 1wpaj: read-side cluster-version gate. This block, not the
            # shared `read_cluster_payload`, is the right place for it: that
            # reader also serves the community tools, the communities resource,
            # and the community labelling reached from call hierarchy and
            # impact, and refusing there would strand all of them. Only this
            # block asserts a base-topology centrality ORDER whose meaning
            # depends on the artifact version. Without the gate the guarantee
            # holds only by the accident of a co-occurring graph-version bump.
            _persisted_cluster_version = str(bw_payload.get("cluster_builder_version") or "")
            _runtime_cluster_version = str(getattr(gc_bw, "CLUSTER_BUILDER_VERSION", "") or "")
            # A MISSING persisted version is treated as stale, not as a pass.
            # Betweenness first appeared at cluster builder version 11, well
            # after the artifact carried a version, so a betweenness section
            # with no version is not a pre-versioning artifact — it is an
            # artifact whose provenance cannot be established, and serving a
            # centrality ORDER on that basis is the thing this gate exists to
            # prevent. Only an unknown RUNTIME version passes ungated, since
            # then there is nothing to compare against.
            if (
                isinstance(bw_section, dict)
                and _runtime_cluster_version
                and _persisted_cluster_version != _runtime_cluster_version
            ):
                bw_section = None
                report["betweenness_stale_artifact"] = {
                    "persisted": _persisted_cluster_version,
                    "runtime": _runtime_cluster_version,
                }
            if isinstance(bw_section, dict) and isinstance(bw_section.get("ranking"), list):
                # Wave 1wpaj: refill from the COMPLETE persisted order when the
                # caller filtered, so an eligible row below the compatibility
                # prefix is reachable. The prefix alone cannot satisfy a
                # filtered limit: eligible rows past rank top_n are invisible.
                _complete = bw_section.get("complete_ranking")
                _source_rows = (
                    _complete if (_eligible is not None and isinstance(_complete, list))
                    else bw_section["ranking"]
                )
                _wanted_rows = max(1, min(limit, 100))
                # Wave 1wpaj: say which view served the rows. `top_n` in the
                # metadata is the persisted PREFIX size, so after a refill it no
                # longer describes how deep the ranking went; a consumer reading
                # it that way would be wrong without this field.
                # Values are deliberately NOT the artifact key names: a leak
                # guard greps the serialized response for those keys, and a
                # field whose VALUE echoes one would trip it for no reason.
                report["betweenness_served_from"] = (
                    "complete_order" if _source_rows is _complete else "prefix"
                )
                bw_rows_served = []
                for row in _source_rows:
                    if not isinstance(row, dict):
                        continue
                    _nid = str(row.get("node_id") or "")
                    if _eligible is not None and not _eligible(_nid):
                        continue
                    _served = dict(row)
                    if "label" not in _served or "kind" not in _served:
                        # Compact complete-order rows resolve their presentation
                        # fields at serve time.
                        _node = index.get_node(_nid) or {}
                        _served.setdefault("label", _node.get("label", _nid))
                        _served.setdefault("kind", _node.get("kind"))
                    bw_rows_served.append(_served)
                    if len(bw_rows_served) >= _wanted_rows:
                        break
                bw_metadata: dict[str, Any] = {
                    "node_count": int(bw_section.get("node_count") or 0),
                    "edge_count": int(bw_section.get("edge_count") or 0),
                    "top_n": int(bw_section.get("top_n") or 0),
                    "elapsed_ms": int(bw_section.get("elapsed_ms") or 0),
                }
                if bw_section.get("cutoff") is not None:
                    bw_metadata["cutoff"] = int(bw_section["cutoff"])
                # Assign report fields only after every cast above succeeded,
                # so a corrupted section can never leave a half-populated
                # response (method set alongside a skipped_reason).
                report["betweenness_method"] = str(bw_section.get("method") or "")
                report["betweenness_metadata"] = bw_metadata
                bw_computed = True
        except Exception:
            bw_rows_served = []
            bw_computed = False
            report.pop("betweenness_method", None)
            report.pop("betweenness_metadata", None)
            # Wave 1wpaj delivery review: this key is assigned before the casts
            # below it, so it has to be torn down here too. Leaving it behind
            # produced a response that named a serving view while also saying
            # the section was not served, which is the half-populated shape the
            # comment above the casts exists to prevent.
            report.pop("betweenness_served_from", None)
        report["betweenness"] = bw_rows_served
        report["betweenness_computed"] = bw_computed
        if not bw_computed and not _collapse_active:
            # Legacy clusters artifact (pre-build-time-betweenness, no section)
            # or no clusters artifact yet — graceful absent-section response,
            # not a crash; the next graph rebuild persists the section.
            # Wave 1wpaj: the vocabulary gains a stale-artifact reason so a
            # version mismatch is reported as itself rather than as an absent
            # section, which would read as "rebuild pending" for a payload that
            # is present but describes a different graph. The collapsed case is
            # handled above and is skipped here so its reason and note are not
            # overwritten with the absent-section wording.
            _stale = bool(report.get("betweenness_stale_artifact"))
            report["betweenness_skipped_reason"] = (
                "betweenness_artifact_stale" if _stale else "betweenness_not_in_artifact"
            )
            # Wave 1wpaj: the note has to match the reason. The stale case is a
            # payload that IS present and describes a different graph, so the
            # "this artifact predates the build-time pass" wording would be a
            # wrong diagnosis even though its remedy happens to be right.
            report["betweenness_note"] = (
                "Betweenness is computed at build time and persisted in the graph "
                "clusters artifact; this artifact was written by a different cluster "
                "builder version, so its ranking does not describe the current graph. "
                "Rebuild the graph index (index_build(content='graph', "
                "mode='rebuild')) to refresh it."
                if _stale else
                "Betweenness is computed at build time and persisted in the graph "
                "clusters artifact; this artifact predates the build-time pass. "
                "Rebuild the graph index (index_build(content='graph', "
                "mode='rebuild')) to populate it."
            )

    # Wave 130rj — field feedback §6.4 + §6.2: emit a
    # `betweenness_dominated_by_generated` warning when >50% of top-N
    # betweenness results are tagged generated.
    # Wave 1wpaj: the fan_in/fan_out/chokepoints loop that used to live here is
    # gone. Those sections come from `report()`, which now filters before it
    # truncates, so post-filtering them would only re-shrink an already correct
    # result. Betweenness is NOT a `report()` section — it is served from the
    # cluster artifact below — so it keeps its post-filter.
    # Wave 1wpaj: betweenness eligibility is applied at the source now, during
    # the refill from the complete persisted order, so no post-filter remains.
    # Post-filtering here would be a no-op on an already-eligible list and would
    # reintroduce the shrink-after-slice shape this wave removed.
    # Wave 130rj (130tw) normalization note: `betweenness_computed` /
    # `betweenness_skipped_reason` are now set directly by the artifact-serving
    # block above (wave 1p9q3 / 1p9q1) — the dict-shaped inline diagnostics that
    # this block used to normalize no longer exist.

    # Compute the dominated warning over the (possibly post-filter) betweenness rows.
    bw_rows = report.get("betweenness") if isinstance(report.get("betweenness"), list) else None
    if bw_rows:
        gen_count = sum(1 for row in bw_rows if isinstance(row, dict) and _node_is_generated(str(row.get("node_id") or "")))
        if gen_count * 2 > len(bw_rows):  # >50%
            report["betweenness_dominated_by_generated"] = True
        else:
            report["betweenness_dominated_by_generated"] = False
    # Wave 13129 (1316p): curated allowlist of common Java stdlib + framework
    # method simple names. The pre-1316p graph-state-based count no longer
    # fires for the common Java case because 1312l's receiver-type resolution
    # at index time eliminates the spurious `external::*` nodes the count
    # depended on. The allowlist answers the operator's actual question.
    # Wave 13129 (13192): extended to multi-language dispatch by source-file
    # extension. Each language has different stdlib patterns; one global
    # allowlist would either over-flag or be ambiguous.
    _STDLIB_COMMON_NAMES_BY_LANG: dict[str, frozenset[str]] = {
        ".java": frozenset({
            # java.lang.Object
            "equals", "hashCode", "toString", "getClass", "notify", "notifyAll", "wait",
            # java.lang.Runnable / Thread
            "run",
            # java.lang.AutoCloseable / Closeable
            "close",
            # java.util.function (Functional interfaces)
            "accept", "apply", "test", "get",
            # java.util.Comparator / Comparable
            "compare", "compareTo",
            # java.util.Iterator / Iterable
            "iterator", "next", "hasNext",
            # java.lang.reflect (commonly mistaken)
            "getMethod", "getDeclaredMethod", "getField", "getDeclaredField",
            # java.io
            "read", "write", "flush", "writeObject", "readObject",
            # java.util.Map.Entry / collections
            "getKey", "getValue",
            # Spring patterns
            "execute", "process", "handle",
        }),
        ".cs": frozenset({
            # System.Object
            "Equals", "GetHashCode", "ToString", "GetType",
            # System.IDisposable
            "Dispose",
            # System.Collections.IEnumerator / IEnumerable
            "MoveNext", "Current", "GetEnumerator",
            # System.IComparable / IComparer
            "Compare", "CompareTo",
            # System.ICloneable
            "Clone",
            # System.IO (stream patterns)
            "Read", "Write", "Close", "Flush",
            # Common method names on services
            "Start", "Stop", "Reset", "Cancel", "Invoke",
            # System.Collections.Generic.List / IDictionary
            "Add", "Remove", "Contains", "Clear", "ToArray", "ToList",
            # Parsing / formatting
            "Format", "Parse", "TryParse",
            # Visitor patterns / .NET internals
            "Visit", "Execute", "Process", "Handle",
        }),
        ".kt": frozenset({
            # Kotlin runs on JVM — inherits Java common method names
            "equals", "hashCode", "toString", "compareTo",
            "iterator", "next", "hasNext", "close", "run",
            "accept", "apply", "test", "get",
            # Kotlin stdlib extension functions commonly used as method names
            "let", "also", "with", "invoke", "getValue", "setValue",
            # Operator overloads
            "plus", "minus", "times", "div", "rangeTo",
        }),
        ".swift": frozenset({
            # Initializers / deinitializers
            "init", "deinit",
            # CustomStringConvertible
            "description", "debugDescription",
            # Hashable / Equatable
            "hash",
            # Codable
            "encode", "decode",
            # Comparable
            "compare",
            # Collection
            "count", "append", "remove", "insert", "contains", "forEach",
            # Sequence
            "map", "filter", "reduce", "compactMap", "flatMap",
            "sorted", "prefix", "suffix", "first", "last", "min", "max",
            "allSatisfy",
            # Indexing
            "index",
        }),
        ".py": frozenset({
            # Dunder methods
            "__init__", "__str__", "__repr__", "__eq__", "__hash__",
            "__len__", "__iter__", "__next__",
            "__enter__", "__exit__", "__call__",
            "__getitem__", "__setitem__", "__delitem__",
            "__contains__", "__bool__",
            "__add__", "__sub__", "__mul__", "__lt__",
            # threading / file IO
            "close", "read", "write", "flush", "run", "start", "join",
        }),
    }
    # Wave 13129 (13198): extended allowlist coverage to JS/TS/Go/Rust/Scala/PHP/Ruby.
    _JS_COMMON = frozenset({
        # Object.prototype
        "toString", "valueOf", "hasOwnProperty", "isPrototypeOf", "propertyIsEnumerable",
        # Promise
        "then", "catch", "finally",
        # Array.prototype
        "forEach", "map", "filter", "reduce", "find", "findIndex",
        "some", "every", "includes", "push", "pop", "shift", "unshift",
        "slice", "splice", "indexOf", "lastIndexOf", "join", "split", "concat",
        # String.prototype
        "charAt", "charCodeAt", "substring", "substr", "toLowerCase", "toUpperCase", "trim",
        # generic
        "length",
    })
    _STDLIB_COMMON_NAMES_BY_LANG[".js"]  = _JS_COMMON
    _STDLIB_COMMON_NAMES_BY_LANG[".jsx"] = _JS_COMMON
    _STDLIB_COMMON_NAMES_BY_LANG[".mjs"] = _JS_COMMON
    _STDLIB_COMMON_NAMES_BY_LANG[".cjs"] = _JS_COMMON

    _TS_COMMON = _JS_COMMON | frozenset({
        # TS framework lifecycle / serialization
        "toJSON", "render",
        # React class component lifecycle
        "componentDidMount", "componentWillUnmount", "componentDidUpdate",
        "shouldComponentUpdate", "getSnapshotBeforeUpdate",
        # Hooks (used as method names occasionally)
        "useState", "useEffect", "useMemo", "useCallback",
    })
    _STDLIB_COMMON_NAMES_BY_LANG[".ts"]  = _TS_COMMON
    _STDLIB_COMMON_NAMES_BY_LANG[".tsx"] = _TS_COMMON

    _STDLIB_COMMON_NAMES_BY_LANG[".go"] = frozenset({
        # io.Reader / io.Writer / io.Closer
        "Read", "Write", "Close",
        # fmt.Stringer / error
        "String", "Error",
        # encoding/json, encoding/xml, encoding/gob, encoding/binary
        "Marshal", "Unmarshal", "Encode", "Decode",
        # sync
        "Wait", "Done", "Lock", "Unlock", "RLock", "RUnlock",
        # http.Handler
        "ServeHTTP",
        # standard runnable patterns
        "Run", "Start", "Stop",
        # Stringer / formatter
        "Format", "Scan", "Reset",
    })

    _STDLIB_COMMON_NAMES_BY_LANG[".rs"] = frozenset({
        # Default / construction
        "new", "default",
        # Clone / Drop / fmt::Debug / Display
        "clone", "drop", "fmt",
        # PartialEq / Ord / PartialOrd
        "eq", "ne", "cmp", "partial_cmp",
        # Hash
        "hash",
        # serde
        "serialize", "deserialize",
        # From / Into / AsRef / AsMut
        "from", "into", "as_ref", "as_mut",
        # Option / Result idioms
        "unwrap", "expect", "ok", "err",
        # Iterator
        "iter", "iter_mut", "into_iter", "next", "collect",
        "map", "filter", "fold", "len",
    })

    _STDLIB_COMMON_NAMES_BY_LANG[".scala"] = frozenset({
        # Scala on JVM — inherits Java common names
        "equals", "hashCode", "toString", "compareTo",
        # Scala-specific apply/unapply/copy
        "apply", "unapply", "copy",
        # Case-class product methods
        "productElement", "productArity", "canEqual",
        # Collection
        "foreach", "map", "flatMap", "filter", "fold", "reduce",
        "collect", "groupBy", "head", "tail", "isEmpty", "nonEmpty",
        # Common
        "run", "execute", "close",
    })

    _STDLIB_COMMON_NAMES_BY_LANG[".php"] = frozenset({
        # PHP magic methods
        "__construct", "__destruct", "__toString",
        "__get", "__set", "__isset", "__unset",
        "__call", "__callStatic", "__invoke",
        "__clone", "__sleep", "__wakeup", "__serialize", "__unserialize",
        # Iterator / Countable / ArrayAccess
        "count", "getIterator",
        "current", "next", "key", "valid", "rewind",
        "offsetGet", "offsetSet", "offsetExists", "offsetUnset",
        # JsonSerializable
        "jsonSerialize",
    })

    _STDLIB_COMMON_NAMES_BY_LANG[".rb"] = frozenset({
        # Object
        "initialize", "to_s", "inspect",
        # Conversions
        "to_a", "to_h", "to_proc", "to_i", "to_f", "to_str",
        # Enumerable
        "each", "each_with_index", "each_with_object",
        "map", "select", "reject", "reduce", "inject",
        "find", "any?", "all?", "none?", "count",
        # Comparable
        "==", "<=>", "eql?",
        # Object identity / cloning
        "hash", "dup", "clone", "object_id",
        # Reflection
        "send", "public_send", "method_missing", "respond_to?",
        "is_a?", "kind_of?", "instance_of?",
        # Standard hooks
        "call",
    })

    def _stdlib_collision_for_node(_node: dict[str, Any], _simple: str) -> int:
        """Return 1 when the project node's simple name appears in the language-specific
        stdlib allowlist (extension-derived from source_file); 0 otherwise. Wave 13192.
        """
        source_file = str(_node.get("source_file") or "")
        # Extract extension; lowercase for case-insensitive match (.JAVA, .Cs etc).
        ext_idx = source_file.rfind(".")
        slash_idx = source_file.rfind("/")
        if ext_idx <= slash_idx:
            return 0
        ext = source_file[ext_idx:].lower()
        allowlist = _STDLIB_COMMON_NAMES_BY_LANG.get(ext)
        if allowlist is None:
            return 0
        return 1 if _simple in allowlist else 0

    # Wave 13129 (1316j): single-source-of-truth simple-name extraction.
    # For symbol nodes (`<file>::<qname>`), take the last `.`-segment of the
    # qname (e.g. `JSON.writeObject` → `writeObject`).
    # For module/file nodes (no `::`), take the basename without extension
    # (e.g. `path/StatusBarManager.swift` → `StatusBarManager`).
    # The pre-1316j behavior took the file extension for module nodes,
    # producing the same constant for every module entry (a consumer reported
    # `same_name_node_count: 72` on every Swift module — the total Swift
    # module count, not a per-symbol value).
    def _node_simple_name(nid: str) -> str:
        if not nid:
            return ""
        if "::" in nid:
            symbol = nid.rsplit("::", 1)[-1]
            return symbol.rsplit(".", 1)[-1]
        # Module/file node: take last path segment, drop extension.
        basename = nid.rsplit("/", 1)[-1]
        if "." in basename:
            return basename.rsplit(".", 1)[0]
        return basename

    # Wave 130rj (130tw): name_collision_count on each ranking entry.
    # Wave 13129 (1312b): decomposed into same_name_node_count + cross_file_collision
    # + external_name_collision_count. The original field is preserved as a
    # deprecated alias for same_name_node_count for one release.
    #
    # Simple-name attribution can over-count fan_in two ways:
    # - same-file aggregation (Swift StatusBarManager nested types) → reflected
    #   in same_name_node_count without cross_file_collision (operator can
    #   verify the file-tree shape is not the actual signal)
    # - external collision (Java JSON.writeObject vs ObjectOutputStream.writeObject)
    #   → reflected in external_name_collision_count > 0
    #
    # The simple-name match uses the last `.`-segment of the symbol part after
    # `::`, identical for project and external nodes (1312b AC-3) — so a project
    # `JSON.writeObject` matches both `external::writeObject` and
    # `external::ObjectOutputStream.writeObject`.
    # Wave 13129 (1316p): only the project-side precompute remains. The
    # external-side precompute (`external_counts_by_simple_name`) is replaced
    # by the curated `_JAVA_STDLIB_COMMON_NAMES` allowlist lookup.
    project_files_by_simple_name: dict[str, set[str]] = {}
    for _node in index.nodes:
        nid = str(_node.get("id") or "")
        if not nid:
            continue
        if nid.startswith("external::"):
            continue
        simple = _node_simple_name(nid)
        if not simple:
            continue
        source_file = str(_node.get("source_file") or "")
        if not source_file:
            # Fall back to file portion of node_id when source_file missing.
            source_file = nid.split("::")[0] if "::" in nid else nid
        project_files_by_simple_name.setdefault(simple, set()).add(source_file)

    project_node_count_by_simple_name: dict[str, int] = {}
    for _node in index.nodes:
        _nid = str(_node.get("id") or "")
        if not _nid or _nid.startswith("external::"):
            continue
        _simple = _node_simple_name(_nid)
        if _simple:
            project_node_count_by_simple_name[_simple] = (
                project_node_count_by_simple_name.get(_simple, 0) + 1
            )

    def _collision_fields(nid: str) -> dict[str, Any]:
        if not nid or nid.startswith("external::"):
            return {
                "same_name_node_count": 1,
                "cross_file_collision": False,
                "external_name_collision_count": 0,
                "name_collision_count": 1,
            }
        simple = _node_simple_name(nid)
        same_name = project_node_count_by_simple_name.get(simple, 1)
        files = project_files_by_simple_name.get(simple, set())
        cross_file = len(files) >= 2
        # Wave 13192: per-language allowlist lookup (extension-derived from
        # source_file). Java was 1316p; this dispatches across .java/.cs/.kt/
        # .swift/.py with curated lists per language.
        node = index.get_node(nid) or {}
        external_count = _stdlib_collision_for_node(node, simple)
        return {
            "same_name_node_count": same_name,
            "cross_file_collision": cross_file,
            "external_name_collision_count": external_count,
            # Deprecated alias preserved for one release (wave 13129 1312b AC-4).
            "name_collision_count": same_name,
        }

    for _section_name in ("fan_in", "fan_out", "chokepoints", "file_hubs", "betweenness"):
        _rows = report.get(_section_name)
        if isinstance(_rows, list):
            for _row in _rows:
                if isinstance(_row, dict):
                    _row.update(_collision_fields(str(_row.get("node_id") or "")))

    # Wave 130rj (130tw): exclude_external filters external::* nodes from
    # the architectural-ranking sections. Independent of exclude_generated —
    # operators typically combine both for "show me MY code" orientation.
    # Wave 1wpaj: nothing remains to post-filter. The four `report()` sections
    # are filtered before truncation inside that method, and betweenness is
    # filtered during its refill from the complete persisted order.

    report["exclude_generated"] = exclude_generated
    report["exclude_external"] = exclude_external
    report["collapse_generated_files"] = collapse_generated_files
    report["collapse_class_module_pairs"] = collapse_class_module_pairs
    report["collapse_package_to_directory"] = collapse_package_to_directory
    # Wave 1p2q3 (1p2q9 B): per-language attribution-confidence counts. wf_graph_report
    # surfaces structural sections (fan_in/out, chokepoints, file_hubs, etc.) but doesn't
    # carry edges directly — compute from the underlying graph edges so the diagnostic
    # reflects the layer's attribution distribution at large.
    report["attribution_counts_by_language"] = server_impl._compute_attribution_counts_by_language(list(index.edges), index)
    return _attach_auto_rebuild_diag(
        server_impl._response(
            "ok",
            report,
            diagnostics=partition_diagnostics or None,
            next_tools=["code_callgraph", "code_impact"],
            usage="code_callgraph(symbol='path::symbol')",
        ),
        index,
    )

def code_graph_path_response(
    root: Path,
    from_symbol: str,
    to_symbol: str,
    *,
    relations: Optional[list[str]] = None,
    max_hops: int = 10,
    layer: str = "project",
    direction: str = "forward",
    min_confidence: str = "EXTRACTED",
) -> dict[str, Any]:
    """Find the shortest connecting path between two symbols in the graph.

    Prefer when: tracing dependency chains, understanding how module A reaches module B,
    or identifying indirect coupling between two symbols. Always returns the consistent
    shape {found, path_nodes, path_edges, hop_count, suggestions} regardless of outcome.

    Response fields:
    - found: true when a path exists within max_hops
    - path_nodes: ordered list of {node_id, label, kind, source_file} from from_symbol to to_symbol
    - path_edges: ordered list of traversed edges; when direction="either" each edge carries
      an extra ``traversal_direction`` field ("forward" or "backward")
    - hop_count: number of edges in the path (0 when symbols are identical, 0 when not found)
    - suggestions: list of {id, label, kind} near-matches when either symbol is unresolvable
    - direction: echoes the requested direction

    Args:
        from_symbol: Starting graph node id or resolvable symbol.
        to_symbol: Target graph node id or resolvable symbol.
        relations: Optional edge relation filter (default: all relations).
        max_hops: Maximum hops before giving up (default 10).
        layer: Graph layer (default ``project``).
        direction: ``forward`` (default), ``backward``, or ``either``. Forward walks outgoing
            edges only; backward walks incoming; either walks both with per-edge
            ``traversal_direction`` annotations.
    """
    from wf_server import server_impl
    direction_value = (direction or "forward").strip().lower()
    if direction_value not in ("forward", "backward", "either"):
        return server_impl._response(
            "error",
            {"from_symbol": from_symbol, "to_symbol": to_symbol, "direction": direction, "found": False, "path_nodes": [], "path_edges": [], "hop_count": 0, "suggestions": []},
            diagnostics=[server_impl._diagnostic("invalid_arguments", f"direction must be 'forward', 'backward', or 'either'; got {direction!r}.")],
            next_tools=["wf_help"],
            usage="code_graph_path(from_symbol='...', to_symbol='...', direction='forward')",
        )
    gq = server_impl._load_graph_query()
    try:
        layer_value = server_impl._graph_layer_value(layer)
    except ValueError as exc:
        return server_impl._response(
            "error",
            {"from_symbol": from_symbol, "to_symbol": to_symbol, "direction": direction_value, "found": False, "path_nodes": [], "path_edges": [], "hop_count": 0, "suggestions": []},
            diagnostics=[server_impl._diagnostic("invalid_arguments", str(exc))],
            next_tools=["wf_help"],
            usage="code_graph_path(from_symbol='...', to_symbol='...')",
        )
    index = gq.get_query_index(root, layer=layer_value)
    if not index.present:
        return server_impl._response(
            "error",
            {"from_symbol": from_symbol, "to_symbol": to_symbol, "direction": direction_value, "found": False, "path_nodes": [], "path_edges": [], "hop_count": 0, "suggestions": []},
            **_graph_unavailable_fields(gq, layer_value, index),
        )
    suggestions: list[dict[str, Any]] = []
    from_id = index.resolve_symbol(from_symbol)
    to_id = index.resolve_symbol(to_symbol)
    # Wave 1304x / 1304r: refresh + reload + re-resolve BOTH symbols if either missed.
    # We can't use _graph_refresh_and_resolve here because it returns (None, None)
    # when its single target symbol still misses post-refresh — that would discard
    # the freshly loaded index even though the OTHER symbol might now resolve.
    if from_id is None or to_id is None:
        def _recheck_both_paths():
            new_index = gq.get_query_index(root, layer=layer_value)
            return (new_index, new_index.resolve_symbol(from_symbol), new_index.resolve_symbol(to_symbol))
        refreshed = server_impl._graph_refresh_then_recheck(root, _recheck_both_paths)
        if refreshed is not None:
            new_index, new_from_id, new_to_id = refreshed
            index = new_index
            if from_id is None:
                from_id = new_from_id
            if to_id is None:
                to_id = new_to_id
    if from_id is None:
        suggestions.extend(server_impl._suggest_near_symbols(index, from_symbol))
    if to_id is None:
        for s in server_impl._suggest_near_symbols(index, to_symbol):
            if s not in suggestions:
                suggestions.append(s)
    if from_id is None or to_id is None:
        missing_label = (
            f"both symbols '{from_symbol}' and '{to_symbol}'" if from_id is None and to_id is None
            else f"'{from_symbol}'" if from_id is None
            else f"'{to_symbol}'"
        )
        return server_impl._response(
            "ok",
            {"from_symbol": from_symbol, "to_symbol": to_symbol, "direction": direction_value, "found": False, "path_nodes": [], "path_edges": [], "hop_count": 0, "suggestions": suggestions},
            diagnostics=[server_impl._diagnostic(
                "graph_symbol_not_found",
                f"Could not resolve {missing_label} to a graph node (refresh attempted).",
                recovery_tools=["code_definition", "code_keyword"],
                recovery_usage=f"code_definition(symbol_or_path_position={from_symbol if from_id is None else to_symbol!r})",
            )],
            next_tools=["code_callhierarchy"],
            usage="code_callhierarchy(symbol='...')",
        )
    try:
        result = index.shortest_path(
            from_id, to_id,
            relations=relations,
            max_hops=max_hops,
            direction=direction_value,
            min_confidence=min_confidence,
        )
    except ValueError as exc:
        return server_impl._response(
            "error",
            {"from_symbol": from_symbol, "to_symbol": to_symbol, "direction": direction_value, "found": False, "path_nodes": [], "path_edges": [], "hop_count": 0, "suggestions": []},
            diagnostics=[server_impl._diagnostic("invalid_arguments", str(exc))],
            next_tools=["wf_help"],
            usage="code_graph_path(from_symbol='...', to_symbol='...', min_confidence='EXTRACTED')",
        )
    # Wave 1p2q3 (1p2q4): structural-path diagnostic. When the resolved path
    # contains zero `calls` edges, the endpoints share structural reachability
    # but no direct call chain — the headline `found: true` is honest, but
    # operators reading the result should know the path is structural-only.
    diagnostics: list[dict[str, Any]] = []
    if result["found"] and result["path_edges"]:
        calls_edges = [e for e in result["path_edges"] if e.get("relation") == "calls"]
        if not calls_edges:
            structural_count = len(result["path_edges"])
            diagnostics.append(server_impl._diagnostic(
                "path_is_structural",
                f"Path connects via {structural_count} imports/defines edge(s), not via calls. "
                "Endpoints share structural reachability but no direct call chain. "
                "Pass `relations=[\"calls\"]` to restrict to call edges only.",
            ))
    return _attach_auto_rebuild_diag(
        server_impl._response(
            "ok",
            {
                "from_symbol": from_symbol,
                "to_symbol": to_symbol,
                "direction": direction_value,
                "layer": layer_value,
                "found": result["found"],
                "path_nodes": result["path_nodes"],
                "path_edges": result["path_edges"],
                "hop_count": result["hop_count"],
                "suggestions": suggestions,
            },
            diagnostics=diagnostics,
            next_tools=["code_callhierarchy", "code_impact"],
            usage=f"code_callhierarchy(symbol={from_symbol!r})",
        ),
        index,
    )

def code_graph_community_response(
    root: Path,
    community_id: str = "",
    *,
    hub_node_id: str = "",
    layer: str = "project",
    limit: int = 50,
    offset: int = 0,
    exclude_generated: bool = False,
) -> dict[str, Any]:
    """Return member nodes of a community, bound to one published generation.

    Wave 1xny6: the pin is what makes the answer coherent. This response reads
    the community membership and then the graph's per-node degree; unpinned,
    a publication between those two reads would report members that the
    degree source no longer contains.
    """
    from wf_server import server_impl
    with server_impl._graph_snapshot_module().pinned(root, "project"):
        return _code_graph_community_response_pinned(
            root, community_id, hub_node_id=hub_node_id, layer=layer,
            limit=limit, offset=offset, exclude_generated=exclude_generated,
        )

def _code_graph_community_response_pinned(
    root: Path,
    community_id: str = "",
    *,
    hub_node_id: str = "",
    layer: str = "project",
    limit: int = 50,
    offset: int = 0,
    exclude_generated: bool = False,
) -> dict[str, Any]:
    """Return member nodes of a community from the published community rows.

    Prefer when: drilling into a specific community identified from wf_graph_report
    or the cluster dashboard. Returns members sorted by degree descending so the
    most-connected nodes appear first.

    Pagination (wave 130rj — field feedback §1.3): default ``limit=50``
    so communities of 50+ members are usable inline. ``total_node_count`` and
    ``has_more`` let the caller page through larger communities. Communities
    under 50 nodes return all members in one call.

    Response fields:
    - community_id: the requested community identifier
    - label: human-readable community label
    - total_node_count: total members of the community (independent of pagination)
    - returned_count: number of members in this response page
    - offset: the requested page offset
    - has_more: true when more members exist past this page
    - nodes: page of {id, label, kind, source_file, degree} sorted by degree descending

    Args:
        community_id: Community ID as returned in the cluster artifact.
        layer: Graph layer (default ``project``).
        limit: Max members in this page (default 50, max 500).
        offset: Member index to start from (default 0). Members are sorted by degree desc.
    """
    from wf_server import server_impl
    # Wave 13129 (1316r): community_id and hub_node_id are alternative inputs.
    # community_id wins when both are provided; hub_node_id is the stable
    # cross-rebuild anchor that resolves to whatever community contains the
    # node (Leiden ids change between rebuilds; node ids don't).
    community_id = (community_id or "").strip()
    hub_node_id = (hub_node_id or "").strip()
    hub_node_id_used = False
    if not community_id and not hub_node_id:
        return server_impl._response(
            "error",
            {"community_id": community_id},
            diagnostics=[server_impl._diagnostic("invalid_arguments",
                                     "Provide either community_id or hub_node_id.")],
            next_tools=["wf_graph_report"],
            usage="wf_graph_report(layer='project')",
        )
    try:
        layer_value = server_impl._graph_layer_value(layer)
    except ValueError as exc:
        return server_impl._response(
            "error",
            {"community_id": community_id},
            diagnostics=[server_impl._diagnostic("invalid_arguments", str(exc))],
            next_tools=["wf_help"],
            usage="code_graph_community(community_id='...')",
        )
    gq = server_impl._load_graph_query()
    try:
        gc = server_impl._load_script("graph_cluster")
    except Exception as exc:
        return server_impl._response(
            "error",
            {"community_id": community_id},
            diagnostics=[server_impl._diagnostic("load_error", f"Failed to load graph_cluster: {exc}")],
            next_tools=["index_build"],
            usage="index_build(content='graph', mode='create')",
        )
    failure = server_impl._graph_snapshot_failure_fields(root)
    if failure:
        return server_impl._response("error", {"community_id": community_id}, **failure)
    payload = gc.read_cluster_payload(root, layer_value)
    if not payload.get("present"):
        return server_impl._response(
            "error",
            {"community_id": community_id},
            diagnostics=[server_impl._diagnostic("cluster_not_ready", "Cluster artifact is absent. Run graph indexing with clustering enabled.")],
            next_tools=["index_build"],
            usage="index_build(content='graph', mode='create')",
        )
    def _find_community(_payload):
        for c in (_payload.get("communities") or []):
            if community_id and str(c.get("community_id") or "") == community_id:
                return c
        return None

    def _find_community_by_hub_node(_payload):
        # Wave 13129 (1316r): resolve hub_node_id to its current community.
        # The hub is identified by membership — any community containing the
        # node id resolves. Leiden produces hard-clustering so node_id matches
        # exactly one community; if multiple match (defensive), first wins.
        for c in (_payload.get("communities") or []):
            members = c.get("node_ids") or []
            if hub_node_id in members:
                return c
        return None

    target: Optional[dict[str, Any]] = None
    if community_id:
        target = _find_community(payload)
    if target is None and hub_node_id:
        target = _find_community_by_hub_node(payload)
        if target is not None:
            hub_node_id_used = True
            # Use the resolved community_id for the response.
            community_id = str(target.get("community_id") or "")
    if target is None:
        # Wave 1304x / 1304r: refresh-then-recheck before emitting suggestions
        def _recheck_community():
            refreshed_payload = gc.read_cluster_payload(root, layer_value)
            return _find_community(refreshed_payload) or {}  # truthy on hit, {} so it's falsy on miss but not None
        refreshed = server_impl._graph_refresh_then_recheck(root, _recheck_community)
        if refreshed:
            target = refreshed
            payload = gc.read_cluster_payload(root, layer_value)
    if target is None:
        suggestions = _suggest_near_communities(payload.get("communities") or [], community_id, n=5)
        return server_impl._response(
            "error",
            {"community_id": community_id, "suggestions": suggestions},
            diagnostics=[server_impl._diagnostic("not_found", f"No community found with id '{community_id}'.")],
            next_tools=["wf_graph_report"],
            usage="wf_graph_report(layer='project')",
        )
    # Load graph to get degree information
    index = gq.get_query_index(root, layer=layer_value)
    node_ids = target.get("node_ids") or []
    nodes: list[dict[str, Any]] = []
    for nid in node_ids:
        n = index.get_node(nid) or {}
        in_deg = len(index._in.get(nid, []))
        out_deg = len(index._out.get(nid, []))
        nodes.append({
            "id": nid,
            "label": n.get("label", nid),
            "kind": n.get("kind"),
            "source_file": n.get("source_file"),
            "generated": bool(n.get("generated")),
            "degree": in_deg + out_deg,
        })
    nodes.sort(key=lambda x: -x["degree"])
    # total_node_count is the community's actual size (pre-filter). Wave 130rj —
    # Field feedback §6.3: exclude_generated filter removes generated members from the
    # response, but the total reflects the unfiltered community so operators can
    # see how much was suppressed.
    total_node_count = len(nodes)
    if exclude_generated:
        nodes = [n for n in nodes if not n.get("generated")]
    # Apply pagination (wave 130rj). Clamp limit/offset to safe ranges.
    safe_limit = max(1, min(int(limit) if limit is not None else 50, 500))
    safe_offset = max(0, int(offset) if offset is not None else 0)
    page = nodes[safe_offset:safe_offset + safe_limit]
    has_more = (safe_offset + len(page)) < total_node_count
    # Wave 13129 (1312j): community_size_class lets callers branch on size without
    # threshold knowledge. Thresholds: <50 small, 50-200 medium, 200+ large.
    if total_node_count < 50:
        community_size_class = "small"
    elif total_node_count <= 200:
        community_size_class = "medium"
    else:
        community_size_class = "large"
    # Wave 130rj (130tw): pagination_hint surfaces the next-page call shape so
    # operators see the truncation and the recovery path in one response.
    # Wave 13129 (1316r): community_hub_node_id is the stable cross-rebuild
    # anchor — the highest-degree member of the community. The pre-pagination
    # `nodes` list is already sorted by degree desc, so nodes[0] is the hub.
    # When the resolved community has zero members (defensive), use the
    # hub_node_id parameter (if provided) or empty string.
    community_hub_node_id = (
        nodes[0]["id"] if nodes
        else (hub_node_id if hub_node_id else "")
    )
    response_payload: dict[str, Any] = {
        "community_id": community_id,
        "label": target.get("label", community_id),
        "total_node_count": total_node_count,
        "returned_count": len(page),
        "offset": safe_offset,
        "has_more": has_more,
        # node_count kept for backward-compat callers; equals returned_count.
        "node_count": len(page),
        # Generated-node fraction surfaced from the cluster artifact (wave 130rj).
        "generated_node_fraction": float(target.get("generated_node_fraction") or 0.0),
        "exclude_generated": exclude_generated,
        # Wave 13129 (1312j): observability field for caller branching.
        "community_size_class": community_size_class,
        # Wave 13129 (1316r): stable cross-rebuild anchor.
        "community_hub_node_id": community_hub_node_id,
        "hub_node_id_used": hub_node_id_used,
        "nodes": page,
    }
    if has_more:
        next_offset = safe_offset + len(page)
        shown_lo = safe_offset + 1
        shown_hi = safe_offset + len(page)
        response_payload["pagination_hint"] = (
            f"Use limit={safe_limit} offset={next_offset} to retrieve the next page "
            f"({shown_lo}-{shown_hi} of {total_node_count} members shown)"
        )
    # Wave 13129 (1312j): large_community_advisory diagnostic — when the community
    # exceeds 200 members, full traversal will burn token budgets at default
    # pagination (60+ round-trips on a 3119-node community). The recovery hint
    # points operators at code_callhierarchy on the hub (the community's most-
    # connected member, looked up here from the in/out degree across page+remaining
    # members) so they can identify the public API without enumerating the whole
    # community. The advisory surfaces ALONGSIDE pagination_hint; both stay
    # available.
    advisory_diagnostics: list[dict[str, Any]] = []
    if community_size_class == "large":
        # Compute hub from the pre-pagination, pre-exclude_generated node list:
        # use the highest-degree node as the hub. (Same algorithm wave 130rj's
        # communities-section hub selection uses.)
        full_nodes_with_degree = nodes  # already sorted by degree desc above (line 11122)
        # When exclude_generated dropped members, `nodes` may be shorter; recover
        # the unfiltered list by re-fetching for hub lookup.
        if exclude_generated:
            # Recompute the unfiltered, degree-sorted list for hub selection.
            unfiltered: list[dict[str, Any]] = []
            for nid in node_ids:
                n = index.get_node(nid) or {}
                in_deg = len(index._in.get(nid, []))
                out_deg = len(index._out.get(nid, []))
                unfiltered.append({
                    "id": nid, "label": n.get("label", nid),
                    "degree": in_deg + out_deg,
                })
            unfiltered.sort(key=lambda x: -x["degree"])
            full_nodes_with_degree = unfiltered
        hub_node = full_nodes_with_degree[0] if full_nodes_with_degree else None
        hub_node_id = hub_node["id"] if hub_node else ""
        recovery_usage = (
            f"code_callhierarchy(symbol='{hub_node_id}', direction='both')"
            if hub_node_id else ""
        )
        advisory_diagnostics.append(server_impl._diagnostic(
            "large_community_advisory",
            (
                f"Community has {total_node_count} members; full traversal will exceed token "
                "budgets at default pagination. Consider `code_callhierarchy` on the hub "
                f"`{hub_node_id}` to identify the community's public API, then narrow with "
                "`code_graph_path` between specific endpoints. Pagination remains available "
                "via the `pagination_hint` if full enumeration is required."
            ),
            recovery_tools=["code_callhierarchy", "code_graph_path"],
            recovery_usage=recovery_usage,
        ))
    usage_target = page[0]['id'] if page else '...'
    return _attach_auto_rebuild_diag(
        server_impl._response(
            "ok",
            response_payload,
            diagnostics=advisory_diagnostics if advisory_diagnostics else None,
            next_tools=["code_callhierarchy", "code_impact"],
            usage=f"code_callhierarchy(symbol='{usage_target}', direction='both')",
        ),
        index,
    )
