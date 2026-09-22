# Containment bootstrap inventory

Owner: Engineering
Status: active
Last verified: 2026-09-21

Wave: `1ymzq handler-module-split-three`

Pre-adoption inventory: 30 named sites, 2 wrapped (one indirect), 9 sub-clause, 19 allowlisted. Captured before primitive source edits. Function bodies below are the exact current source contract, including returns, predicates and exception scopes; caller rows are a conservative AST name-match inventory (attribute receiver collisions remain possible). Dynamic dispatch and text references require the adoption owner to check each affected module. Tests are included in the caller scan. No production import/adoption is authorized before R0.

## Membership and staging

Register `path_containment.py` before new-baseline R0. Supported conditional route independently reviewed in readiness-review.md (fresh architecture section), then corroborated by QA source reads: retrieval_eval._call_public_path -> code_ask_response -> WaveIndex.search_combined -> _graph_signal_candidates -> graph_query.get_query_index -> _ensure_graph_builder_current -> dynamically loaded indexer.build_index(content="graph") -> index_state_store.finalize_build_epoch -> memory_backfill.authorize_index_finalize/restage_index_finalize -> inventory_closed_waves -> _wave_status -> _contained_source_file. Requires stale graph and backfill publication context; ordinary benchmark execution is not claimed. The unchanged indexer containment helper is NOT the justification.

Only unused primitive, focused tests and evaluator membership/identity proof precede R0. No production caller import yet, therefore no purge entry at bootstrap. Later adoption must choose per-call imports or add a purge entry if server_impl imports the primitive at module top. R1 precedes index extraction; R2 establishes the next evaluator baseline.

## Sites

### `indexer._is_relative_to`

Class: allowlisted. Preserve raising OSError/RuntimeError and all seven callers; explicit-request removal veto must abort on uncertainty. Follow-up: reconsider only in a separately reviewed contract-specific change.

Source: `.wavefoundry/framework/scripts/indexer.py:1304`.

Caller/name-reference candidates:
`server_impl.py:1261` `server_impl.py:1421` `indexer.py:3995` `indexer.py:1661` `indexer.py:1725` `indexer.py:3786` `indexer.py:3922` `indexer.py:3926` `indexer.py:4338` `tests/test_indexer.py:889`

Current predicate and failure contract:

```python
def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False
```

### `context_efficiency._contained_prompt`

Class: sub-clause. Preserve every surrounding resolution/exception boundary, canonical/existence/type/symlink condition and return spelling; replace containment clause only.

Source: `.wavefoundry/framework/scripts/context_efficiency.py:254`.

Caller/name-reference candidates:
`context_efficiency.py:957`

Current predicate and failure contract:

```python
def _contained_prompt(root: Path, relative: Path) -> Optional[Path]:
    try:
        resolved_root = Path(root).resolve(strict=True)
        prompt = (resolved_root / relative).resolve(strict=True)
        if not prompt.is_relative_to(resolved_root) or not prompt.is_file():
            return None
        return prompt
    except (OSError, RuntimeError, ValueError):
        return None
```

### `context_efficiency.contained_stat_signature`

Class: allowlisted. Stat snapshot and FileVersion return contract are distinct; retain strict regular-file observation. Follow-up: reconsider only in a separately reviewed contract-specific change.

Source: `.wavefoundry/framework/scripts/context_efficiency.py:232`.

Caller/name-reference candidates:
`context_efficiency.py:817` `server_impl.py:22164` `tests/test_context_efficiency.py:200` `tests/test_context_efficiency.py:227` `tests/test_context_efficiency.py:178`

Current predicate and failure contract:

```python
def contained_stat_signature(
    root: Path, path: str | Path
) -> Optional[FileVersion]:
    """Stat one contained regular file, returning ``None`` on uncertainty.

    This helper does not create files and never reads file contents.
    """

    try:
        resolved_root = Path(root).resolve(strict=True)
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = resolved_root / candidate
        resolved = candidate.resolve(strict=True)
        if not resolved.is_relative_to(resolved_root) or not resolved.is_file():
            return None
        return FileVersion.from_stat(resolved.stat())
    except (OSError, RuntimeError, ValueError):
        return None
```

### `memory_backfill._contained_source_file`

Class: sub-clause. Preserve every surrounding resolution/exception boundary, canonical/existence/type/symlink condition and return spelling; replace containment clause only.

Source: `.wavefoundry/framework/scripts/memory_backfill.py:156`.

Caller/name-reference candidates:
`memory_backfill.py:178` `memory_backfill.py:234` `memory_supply.py:226` `memory_supply.py:354` `memory_supply.py:429` `memory_supply.py:241`

Current predicate and failure contract:

```python
def _contained_source_file(root: Path, wave_dir: Path, path: Path) -> bool:
    """Accept only ordinary files physically contained by this project wave."""

    try:
        waves_real = _canonical_waves_dir(root)
        if waves_real is None:
            return False
        wave_real = wave_dir.resolve(strict=True)
        path_real = path.resolve(strict=True)
        return (
            not wave_dir.is_symlink()
            and not path.is_symlink()
            and wave_real.is_relative_to(waves_real)
            and path_real.is_relative_to(wave_real)
            and path.is_file()
        )
    except (OSError, RuntimeError):
        return False
```

### `memory_backfill._canonical_waves_dir`

Class: allowlisted. Canonical record-layout loading and directory/existence diagnostics, with OSError translation. Follow-up: reconsider only in a separately reviewed contract-specific change.

Source: `.wavefoundry/framework/scripts/memory_backfill.py:125`.

Caller/name-reference candidates:
`memory_backfill.py:193` `memory_backfill.py:160` `tests/test_record_layout_cold_sites.py:79`

Current predicate and failure contract:

```python
def _canonical_waves_dir(root: Path) -> Path | None:
    """Return the contained physical waves root, rejecting parent escapes."""

    import record_paths  # record roots (wave 1y0gz); lazy like the other sibling imports

    try:
        waves_dir = record_paths.load_record_roots(root).waves
    except record_paths.RecordLayoutInvalid as exc:
        # The resolver already refused (for example the waves root is a symlink
        # escaping the repository); keep this site's OSError contract so the
        # inventory callers report historical_memory_inventory_failed.
        raise OSError(f"historical-memory waves directory refused: {exc}") from exc
    if not waves_dir.exists() and not waves_dir.is_symlink():
        return None
    try:
        root_real = root.resolve(strict=True)
        waves_real = waves_dir.resolve(strict=True)
        if (
            not waves_dir.is_dir()
            or not waves_real.is_relative_to(root_real)
        ):
            raise OSError(
                "historical-memory waves directory escapes the repository root"
            )
        return waves_real
    except RuntimeError as exc:
        raise OSError(
            "historical-memory waves directory could not be resolved safely"
        ) from exc
```

### `memory_supply._contained_source_file`

Class: sub-clause. Preserve every surrounding resolution/exception boundary, canonical/existence/type/symlink condition and return spelling; replace containment clause only.

Source: `.wavefoundry/framework/scripts/memory_supply.py:114`.

Caller/name-reference candidates:
`memory_backfill.py:178` `memory_backfill.py:234` `memory_supply.py:226` `memory_supply.py:354` `memory_supply.py:429` `memory_supply.py:241`

Current predicate and failure contract:

```python
def _contained_source_file(wave_dir: Path, path: Path) -> bool:
    try:
        wave_real = wave_dir.resolve(strict=True)
        path_real = path.resolve(strict=True)
        return (
            not wave_dir.is_symlink()
            and not path.is_symlink()
            and path_real.is_relative_to(wave_real)
            and path.is_file()
        )
    except (OSError, RuntimeError):
        return False
```

### `memory_records._contained_record_path`

Class: sub-clause. Preserve every surrounding resolution/exception boundary, canonical/existence/type/symlink condition and return spelling; replace containment clause only.

Source: `.wavefoundry/framework/scripts/memory_records.py:759`.

Caller/name-reference candidates:
`memory_records.py:948` `memory_records.py:1032` `memory_records.py:1099` `memory_records.py:1328` `memory_records.py:624` `memory_records.py:830` `memory_handlers.py:660` `tests/test_memory_records.py:130`

Current predicate and failure contract:

```python
def _contained_record_path(root: Path, memory_id: str) -> Path:
    """Grammar-validated id → record path, with full resolved containment.

    Raises ValueError when the id is invalid OR the memory root is not
    canonically in-repo (symlink escape) OR the resolved record path would sit
    outside the canonical root. NEVER creates directories — the caller does
    ``mkdir`` only after this returns.
    """
    memory_id = validate_memory_id(memory_id)
    memory_root = canonical_memory_root(root)
    if memory_root is None:
        raise ValueError(
            "memory root resolves outside its canonical repository location "
            "(symlinked memory directory or ancestor) — refusing"
        )
    repo = root.resolve()
    expected_root = repo / MEMORY_DIR
    path = memory_root / f"{memory_id}.md"
    resolved = path.resolve()
    if resolved.parent != expected_root or not resolved.is_relative_to(repo):
        raise ValueError(f"memory id {memory_id!r} escapes the memory root")
    return path
```

### `memory_records._contained_memory_subdir_path`

Class: sub-clause. Preserve every surrounding resolution/exception boundary, canonical/existence/type/symlink condition and return spelling; replace containment clause only.

Source: `.wavefoundry/framework/scripts/memory_records.py:783`.

Caller/name-reference candidates:
`memory_records.py:1329` `memory_records.py:831`

Current predicate and failure contract:

```python
def _contained_memory_subdir_path(root: Path, memory_id: str, subdir: str) -> Path:
    """Resolve one reserved memory subdirectory path without allowing escapes."""
    memory_id = validate_memory_id(memory_id)
    if subdir not in ("archive", "pointers"):
        raise ValueError(f"unknown memory subdirectory: {subdir!r}")
    memory_root = canonical_memory_root(root)
    if memory_root is None:
        raise ValueError(
            "memory root resolves outside its canonical repository location "
            "(symlinked memory directory or ancestor) — refusing"
        )
    repo = root.resolve()
    expected_parent = repo / MEMORY_DIR / subdir
    path = memory_root / subdir / f"{memory_id}.md"
    resolved = path.resolve()
    if resolved.parent != expected_parent or not resolved.is_relative_to(repo):
        raise ValueError(f"memory id {memory_id!r} escapes the {subdir} directory")
    return path
```

### `memory_records._contained_purge_staging_path`

Class: sub-clause. Preserve every surrounding resolution/exception boundary, canonical/existence/type/symlink condition and return spelling; replace containment clause only.

Source: `.wavefoundry/framework/scripts/memory_records.py:803`.

Caller/name-reference candidates:
`memory_records.py:1429` `memory_records.py:832`

Current predicate and failure contract:

```python
def _contained_purge_staging_path(root: Path, memory_id: str) -> Path:
    """Resolve the index-excluded purge staging path without allowing escapes."""
    memory_id = validate_memory_id(memory_id)
    memory_root = canonical_memory_root(root)
    if memory_root is None:
        raise ValueError(
            "memory root resolves outside its canonical repository location "
            "(symlinked memory directory or ancestor) — refusing"
        )
    repo = root.resolve()
    expected_parent = repo / MEMORY_ARCHIVE_DIR / ".purge-staging"
    path = memory_root / "archive" / ".purge-staging" / f"{memory_id}.md"
    resolved = path.resolve()
    if resolved.parent != expected_parent or not resolved.is_relative_to(repo):
        raise ValueError(f"memory id {memory_id!r} escapes the purge staging directory")
    return path
```

### `memory_records.canonical_memory_root`

Class: allowlisted. Exact canonical equality and unresolved return; root resolution remains outside catch. Follow-up: reconsider only in a separately reviewed contract-specific change.

Source: `.wavefoundry/framework/scripts/memory_records.py:733`.

Caller/name-reference candidates:
`memory_records.py:341` `memory_records.py:521` `memory_records.py:591` `memory_records.py:768` `memory_records.py:788` `memory_records.py:806` `memory_records.py:1241` `memory_records.py:1294` `memory_handlers.py:114` `tests/test_memory_records.py:2115`

Current predicate and failure contract:

```python
def canonical_memory_root(root: Path) -> Optional[Path]:
    """The memory root IFF it resolves to its canonical in-repo location.

    THE single containment chokepoint (delivery-review finding): every read
    (load/search/advisory/signature) AND write (add/reconcile) path resolves
    the memory root through here BEFORE traversing or mutating it. A symlinked
    ``docs/agents/memory`` — or any symlinked ancestor — that redirects the
    canonical path outside the repo returns None (readers degrade to empty;
    writers raise). ``resolve()`` follows every existing symlink component and
    appends the non-existent tail, so a symlinked ancestor is caught even
    before the ``memory`` child exists. Both sides are resolved, so a
    legitimately symlinked repo root (macOS ``/var``→``/private/var``) is not a
    false reject. The RETURNED path is unresolved so callers' repo-relative
    math against the unresolved ``root`` is unaffected.
    """
    repo = root.resolve()
    expected = repo / MEMORY_DIR
    memory_root = root / MEMORY_DIR
    try:
        if memory_root.resolve() != expected:
            return None
    except OSError:
        return None
    return memory_root
```

### `memory_records._purge_disposition_path`

Class: allowlisted. Authority refuses final/parent links and returns unresolved path; raising contract. Follow-up: reconsider only in a separately reviewed contract-specific change.

Source: `.wavefoundry/framework/scripts/memory_records.py:1180`.

Caller/name-reference candidates:
`memory_records.py:1194` `memory_records.py:1220`

Current predicate and failure contract:

```python
def _purge_disposition_path(root: Path) -> Path:
    root_resolved = root.resolve()
    path = root / MEMORY_PURGE_DISPOSITIONS
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError("memory purge disposition authority must not be a symlink")
    try:
        path.parent.resolve().relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError("memory purge disposition authority escapes repository root") from exc
    return path
```

### `render_agent_surfaces._contained_review_carrier_path`

Class: wrapped. Resolve root/candidate at existing boundaries; retain strict=False, candidate OSError diagnostic/cause and candidate RuntimeError propagation. Additional primitive resolution must be fault-injection proven.

Source: `.wavefoundry/framework/scripts/render_agent_surfaces.py:1652`.

Caller/name-reference candidates:
`techdocs_audit_lib.py:964` `render_agent_surfaces.py:1729` `render_agent_surfaces.py:1730` `render_agent_surfaces.py:2468` `render_agent_surfaces.py:1858` `render_agent_surfaces.py:1937` `render_agent_surfaces.py:1986` `render_agent_surfaces.py:2027` `render_agent_surfaces.py:2068` `render_agent_surfaces.py:2307` `render_agent_surfaces.py:2442` `render_agent_surfaces.py:2241` `wave_lint_lib/core_validators.py:461`

Current predicate and failure contract:

```python
def _contained_review_carrier_path(repo_root: Path, destination: str) -> Path:
    """Resolve one registered carrier and refuse writes outside ``repo_root``.

    Carrier destinations are fixed by the typed registry, but an existing
    repository can place a symlink at the destination or in one of its parent
    directories.  Setup, upgrade, and direct rendering must not follow that
    repository-controlled path into a sibling directory.  Returning the
    resolved path also prevents a later open from re-following the symlink
    chain that was checked here.
    """

    root = repo_root.resolve()
    candidate = repo_root / destination
    try:
        resolved = candidate.resolve(strict=False)
    except OSError as exc:
        raise RuntimeError(
            f"review carrier path cannot be resolved safely: {destination}: {exc}"
        ) from exc
    if not resolved.is_relative_to(root):
        raise RuntimeError(
            "review carrier path escapes the repository root through a symlink: "
            f"{destination}"
        )
    return resolved
```

### `server_impl._contained_wave_review_paths`

Class: sub-clause. Preserve every surrounding resolution/exception boundary, canonical/existence/type/symlink condition and return spelling; replace containment clause only.

Source: `.wavefoundry/framework/scripts/server_impl.py:8570`.

Caller/name-reference candidates:
`server_impl.py:8628` `server_impl.py:8503` `server_impl.py:14412` `server_impl.py:7211` `tests/test_record_layout_nested.py:356` `tests/test_record_layout_nested.py:353` `tests/test_record_layout_nested.py:351`

Current predicate and failure contract:

```python
def _contained_wave_review_paths(root: Path, wave_md: Path) -> tuple[Path, Path]:
    """Resolve the fixed wave/event paths and reject any repository escape."""

    root_resolved = root.resolve()
    roots = record_paths.load_record_roots(root)
    expected_waves_root = root_resolved.joinpath(*roots.waves_rel.split("/"))
    waves_root = roots.waves.resolve(strict=False)
    if waves_root != expected_waves_root:
        raise ValueError(f"{roots.waves_rel} must resolve to the canonical in-repository directory")
    wave_dir = wave_md.parent.resolve(strict=False)
    # Wave 1y043: a wave folder sits at depth 1 (flat) or within `max_depth`
    # (nested) of the waves root; the default layout keeps the direct-child rule.
    allowed_depth = roots.max_depth if roots.nested else 1
    try:
        depth_parts = wave_dir.relative_to(waves_root).parts
    except ValueError as exc:
        raise ValueError(f"wave directory must resolve inside {roots.waves_rel}") from exc
    if not (1 <= len(depth_parts) <= allowed_depth):
        raise ValueError(
            f"wave directory must resolve to a wave folder within {allowed_depth} level(s) of {roots.waves_rel}"
        )
    try:
        wave_dir.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError("wave directory resolves outside the repository") from exc
    expected_wave_md = wave_dir / "wave.md"
    if wave_md.resolve(strict=False) != expected_wave_md:
        raise ValueError("wave.md must not resolve through a file symlink")
    expected_events = wave_dir / "events.jsonl"
    if expected_events.resolve(strict=False) != expected_events:
        raise ValueError("events.jsonl must not resolve through a file symlink")
    return expected_wave_md, expected_events
```

### `server_impl.resolve_path_under_root`

Class: sub-clause. Preserve every surrounding resolution/exception boundary, canonical/existence/type/symlink condition and return spelling; replace containment clause only.

Source: `.wavefoundry/framework/scripts/server_impl.py:3900`.

Caller/name-reference candidates:
`server_impl.py:7114` `tests/test_server_tools.py:934` `tests/test_server_tools.py:945`

Current predicate and failure contract:

```python
def resolve_path_under_root(repo_root: Path, user_path: str) -> tuple[Optional[Path], Optional[dict[str, Any]]]:
    """Resolve a user-supplied path to an absolute path confined under repo_root.

    Intended for future file navigation tools. Returns ``(path, None)`` on success or
    ``(None, diagnostic)`` when the path escapes allowed roots or cannot be resolved.
    """
    root = repo_root.resolve()
    raw = Path(user_path.strip()).expanduser()
    try:
        candidate = raw.resolve() if raw.is_absolute() else (root / raw).resolve()
    except (OSError, RuntimeError) as exc:
        return None, _diagnostic(
            "path_resolution_failed",
            str(exc),
            recovery_tools=["wf_validate_docs", "wf_current_wave"],
            recovery_usage="wf_validate_docs()",
        )
    try:
        candidate.relative_to(root)
    except ValueError:
        return None, _diagnostic(
            "path_outside_allowed_roots",
            f"Path {user_path!r} resolves outside the configured repository root.",
            recovery_tools=["wf_current_wave", "wf_validate_docs"],
            recovery_usage="wf_current_wave()",
        )
    return candidate, None
```

### `server_impl._resolve_repo_path`

Class: allowlisted. Code-navigation boundary refuses absolute inputs and catches only ValueError/OSError. Follow-up: reconsider only in a separately reviewed contract-specific change.

Source: `.wavefoundry/framework/scripts/server_impl.py:16625`.

Caller/name-reference candidates:
`codenav_handlers.py:370` `codenav_handlers.py:1397` `codenav_handlers.py:1610` `codenav_handlers.py:2696` `graph_handlers.py:608`

Current predicate and failure contract:

```python
def _resolve_repo_path(root: Path, user_path: str) -> Optional[Path]:
    """Resolve *user_path* to an absolute path that is guaranteed to be inside *root*.

    Returns ``None`` if the path escapes the root (path traversal attempt) or if
    it is absolute (only repo-relative paths are accepted).  The returned path is
    not guaranteed to exist — callers must check.
    """
    # Reject absolute paths immediately
    if user_path.startswith("/") or (len(user_path) > 1 and user_path[1] == ":"):
        return None
    try:
        resolved = (root / user_path).resolve()
        root_resolved = root.resolve()
        resolved.relative_to(root_resolved)  # raises ValueError if outside root
        return resolved
    except (ValueError, OSError):
        return None
```

### `techdocs_audit_lib._contained`

Class: wrapped/indirect. Keep renderer delegation as indirect adoption to preserve root OSError propagation and RuntimeError-to-None boundary.

Source: `.wavefoundry/framework/scripts/techdocs_audit_lib.py:952`.

Caller/name-reference candidates:
`techdocs_audit_lib.py:1371`

Current predicate and failure contract:

```python
def _contained(repo_root: Path, rel: str) -> "Path | None":
    """Resolve *rel* under the root, or None when it escapes.

    Uses the shared helper (`render_agent_surfaces._contained_review_carrier_path`),
    which raises on escape; its message names a review carrier, so the caller maps
    the refusal to this module's own degrade token instead of echoing it.
    `server_impl.resolve_path_under_root` is deliberately NOT used: it returns a
    server envelope fragment, and `server_impl` imports this module.
    """
    from render_agent_surfaces import _contained_review_carrier_path  # noqa: PLC0415

    try:
        return _contained_review_carrier_path(repo_root, rel)
    except RuntimeError:
        return None
```

### `techdocs_audit_lib._inside`

Class: allowlisted. Nested lexical string-prefix predicate on previously resolved values; no independent resolution. Follow-up: reconsider only in a separately reviewed contract-specific change.

Source: `.wavefoundry/framework/scripts/techdocs_audit_lib.py:1024`.

Caller/name-reference candidates:
`techdocs_audit_lib.py:1052` `techdocs_audit_lib.py:1070`

Current predicate and failure contract:

```python
def _inside(real: str) -> bool:
        return real == resolved_root or real.startswith(resolved_root + os.sep)
```

### `review_policy.contained_relative_path`

Class: sub-clause. Preserve every surrounding resolution/exception boundary, canonical/existence/type/symlink condition and return spelling; replace containment clause only.

Source: `.wavefoundry/framework/scripts/review_policy.py:1138`.

Caller/name-reference candidates:
`review_policy_reconcile.py:435` `review_policy_reconcile.py:415` `review_policy_reconcile.py:322`

Current predicate and failure contract:

```python
def contained_relative_path(root: Path, relative: str) -> Path:
    """Resolve a registry destination without permitting symlink escape."""

    root_real = root.resolve(strict=True)
    target = root / relative
    cursor = root
    for part in Path(relative).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError(f"review-policy carrier may not traverse symlink: {relative}")
    resolved = target.resolve(strict=False)
    if not resolved.is_relative_to(root_real):
        raise ValueError(f"review-policy carrier escapes root: {relative}")
    return target
```

### `retrieval_eval._path_under_root`

Class: allowlisted. Returns relative POSIX string; catches only ValueError; changing evaluator body would move receipt identity. Follow-up: reconsider only in a separately reviewed contract-specific change.

Source: `.wavefoundry/framework/scripts/retrieval_eval.py:762`.

Caller/name-reference candidates:
`retrieval_eval.py:776`

Current predicate and failure contract:

```python
def _path_under_root(path: Path, root: Path) -> str | None:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None
```

### `retrieval_eval.confined_report_path`

Class: allowlisted. Report publication authority includes filename, role, parent, lstat and protected-report rules. Follow-up: reconsider only in a separately reviewed contract-specific change.

Source: `.wavefoundry/framework/scripts/retrieval_eval.py:846`.

Caller/name-reference candidates:
`retrieval_eval.py:1046` `retrieval_eval.py:1062` `retrieval_eval.py:2773` `retrieval_eval.py:2775` `tests/test_retrieval_eval.py:2386` `tests/test_retrieval_eval.py:2443` `tests/test_retrieval_eval.py:2398` `tests/test_retrieval_eval.py:2408` `tests/test_retrieval_eval.py:2416` `tests/test_retrieval_eval.py:2423` `tests/test_retrieval_eval.py:2445` `tests/test_retrieval_eval.py:2379` `tests/test_retrieval_eval.py:2433` `tests/test_retrieval_eval.py:2437`

Current predicate and failure contract:

```python
def confined_report_path(root: Path, candidate: Path | str, *, role: str) -> Path:
    """Validate one report path and return it, WITHOUT creating anything.

    Parent directories are never created: a caller-selected parent is exactly
    the escape this confinement exists to refuse.
    """
    base = Path(os.path.realpath(root))
    reports = base.joinpath(*REPORT_DIRECTORY_PARTS)
    _assert_confining_ancestors(base)
    supplied = Path(os.path.abspath(Path(candidate)))
    name = supplied.name
    # The PARENT is resolved (a symlinked ``docs`` or ``docs/reports`` lands
    # somewhere that is not the report directory and is refused here as well as
    # by the ancestor assertion above); the FINAL component never is, so a
    # symlinked destination cannot masquerade as a confined regular file.
    parent = Path(os.path.realpath(supplied.parent))
    _require(parent == reports, "report_path_unconfined",
             f"{role} path must be a direct child of {reports}: {supplied}")
    _require(name and name not in (os.curdir, os.pardir), "report_path_unconfined",
             f"{role} path does not name a file: {supplied}")
    _require(name.startswith(REPORT_BASENAME_PREFIX), "report_path_unconfined",
             f"{role} basename must begin with {REPORT_BASENAME_PREFIX!r}: {name}")
    resolved = reports / name
    if role != "temporary":
        _require(not _REPORT_TEMP_RE.match(resolved.name), "report_path_unconfined",
                 f"{role} basename is reserved for publish temporaries: {resolved.name}")
    if role == "output":
        relative = resolved.relative_to(base).as_posix()
        _require(relative not in PROTECTED_REPORT_PATHS, "report_path_protected",
                 f"protected closed-1seaw receipt cannot be a destination: {relative}")
    try:
        entry = os.lstat(resolved)
    except FileNotFoundError:
        return resolved
    except OSError as exc:
        raise EvaluationInvalid("report_path_unconfined",
                                f"{role} path is unusable: {resolved} ({exc})") from exc
    _require(not stat.S_ISLNK(entry.st_mode), "report_path_unconfined",
             f"{role} path is a symlink: {resolved}")
    _require(stat.S_ISREG(entry.st_mode), "report_path_unconfined",
             f"{role} path is not a regular file: {resolved}")
    return resolved
```

### `docs_gardener._under_a_scan_root`

Class: allowlisted. Multi-root scan predicate; caller supplies candidate state; preserve loop/error behavior. Follow-up: reconsider only in a separately reviewed contract-specific change.

Source: `.wavefoundry/framework/scripts/docs_gardener.py:95`.

Caller/name-reference candidates:
`docs_gardener.py:136` `docs_gardener.py:148`

Current predicate and failure contract:

```python
def _under_a_scan_root(scan_roots: list[Path], candidate: Path) -> bool:
    for scan_root in scan_roots:
        try:
            candidate.relative_to(scan_root.resolve())
            return True
        except ValueError:
            continue
    return False
```

### `dashboard_server._asset_path`

Class: allowlisted. Fixed asset root and FileNotFoundError contract. Follow-up: reconsider only in a separately reviewed contract-specific change.

Source: `.wavefoundry/framework/scripts/dashboard_server.py:685`.

Caller/name-reference candidates:
`dashboard_server.py:780`

Current predicate and failure contract:

```python
def _asset_path(name: str) -> Path:
    asset_root = ASSET_ROOT.resolve()
    candidate = (ASSET_ROOT / name).resolve()
    if not candidate.is_relative_to(asset_root):
        raise FileNotFoundError(name)
    return candidate
```

### `setup_readiness._safe`

Class: allowlisted. ObservationError contract and unresolved return. Follow-up: reconsider only in a separately reviewed contract-specific change.

Source: `.wavefoundry/framework/scripts/setup_readiness.py:75`.

Caller/name-reference candidates:
`sqlite_storage_migration.py:187` `sqlite_storage_migration.py:200` `sqlite_storage_migration.py:351` `sqlite_storage_migration.py:418` `sqlite_storage_migration.py:451` `sqlite_storage_migration.py:1608` `sqlite_storage_migration.py:1609` `sqlite_storage_migration.py:1650` `sqlite_storage_migration.py:1654` `sqlite_storage_migration.py:2215` `sqlite_storage_migration.py:189` `sqlite_storage_migration.py:1058` `sqlite_storage_migration.py:1334` `sqlite_storage_migration.py:1484` `sqlite_storage_migration.py:1980` `sqlite_storage_migration.py:2054` `sqlite_storage_migration.py:2059` `sqlite_storage_migration.py:2070` `sqlite_storage_migration.py:2123` `sqlite_storage_migration.py:2185` `sqlite_storage_migration.py:2226` `sqlite_storage_migration.py:194` `sqlite_storage_migration.py:1063` `sqlite_storage_migration.py:1772` `sqlite_storage_migration.py:2046` `sqlite_storage_migration.py:2193` `sqlite_storage_migration.py:1065` `sqlite_storage_migration.py:1067` `sqlite_storage_migration.py:1731` `sqlite_storage_migration.py:1904` `sqlite_storage_migration.py:2048` `sqlite_storage_migration.py:2079` `sqlite_storage_migration.py:2195` `sqlite_storage_migration.py:1362` `sqlite_storage_migration.py:2299` `setup_index.py:2075` `setup_readiness.py:698` `setup_readiness.py:330` `setup_readiness.py:489` `setup_readiness.py:509` `setup_readiness.py:678` `setup_readiness.py:494` `setup_readiness.py:521` `setup_readiness.py:522` `setup_readiness.py:151` `setup_readiness.py:448` `setup_readiness.py:631` `setup_readiness.py:535` `setup_readiness.py:502` `setup_readiness.py:499` `setup_readiness.py:529` `accel_embedder.py:557` `accel_embedder.py:813` `accel_embedder.py:837` `accel_embedder.py:562` `accel_embedder.py:818` `setup_reconciliation.py:34` `setup_reconciliation.py:41` `setup_reconciliation.py:45` `tests/test_sqlite_storage_migration.py:609` `tests/test_sqlite_storage_migration.py:606` `tests/test_sqlite_storage_migration.py:660`

Current predicate and failure contract:

```python
def _safe(root: Path, relative: str) -> Path:
    path = root / relative
    if not path.resolve().is_relative_to(root.resolve()):
        raise ObservationError(f'path escapes repository: {relative}')
    return path
```

### `record_paths._resolved_inside`

Class: allowlisted. Hot-loop contract pins os.path.realpath and forbids Path.resolve. Follow-up: reconsider only in a separately reviewed contract-specific change.

Source: `.wavefoundry/framework/scripts/record_paths.py:119`.

Caller/name-reference candidates:
`record_paths.py:270`

Current predicate and failure contract:

```python
def _resolved_inside(root: Path, candidate: Path) -> bool:
    """True when ``candidate`` resolves inside ``root`` (symlink-aware).
    Uses ``os.path.realpath`` rather than ``Path.resolve`` so the docs-lint
    hot loop, which pins that it never calls ``Path.resolve``, stays clean."""
    try:
        Path(os.path.realpath(candidate)).relative_to(os.path.realpath(root))
        return True
    except (ValueError, OSError):
        return False
```

### `lifecycle_gates._framework_test_receipt_status`

Class: allowlisted. Receipt verifier with structured not-proven diagnostics; containment is only one gate. Follow-up: reconsider only in a separately reviewed contract-specific change.

Source: `.wavefoundry/framework/scripts/lifecycle_gates.py:401`.

Caller/name-reference candidates:
`lifecycle_gates.py:592` `tests/test_server_tools_lifecycle.py:2748` `tests/test_server_tools_lifecycle.py:2756` `tests/test_server_tools_lifecycle.py:2764` `tests/test_server_tools_lifecycle.py:2775` `tests/test_server_tools_lifecycle.py:2894` `tests/test_server_tools_lifecycle.py:2906` `tests/test_server_tools_lifecycle.py:2921` `tests/test_server_tools_lifecycle.py:2884` `tests/test_server_tools_lifecycle.py:2773` `tests/test_server_tools_lifecycle.py:2790` `tests/test_server_tools_lifecycle.py:2933`

Current predicate and failure contract:

```python
def _framework_test_receipt_status(root: Path) -> dict[str, Any]:
    """Verify the existing ``test-cache.json`` receipt without running anything.

    ``run_tests.py`` writes the receipt only after a SUCCESSFUL run of the WHOLE
    suite, with an ``inputs_hash`` covering every file under
    ``.wavefoundry/framework/`` except ``VERSION``, ``MANIFEST``, the cache
    itself, ``test-run.lock``, and the ``index`` / ``__pycache__`` /
    ``.pytest_cache`` directories, so it self-invalidates the moment any
    framework file changes.  A missing, red, stale, or unreadable receipt is reported as NOT
    PROVEN rather than assumed green.

    Scope has TWO halves and both matter (delivery reverification found the
    first wording asserted one and negated the other).  The hash covers
    ``.wavefoundry/framework/`` only, so a documentation edit never makes a
    standing receipt stale -- but the receipt is written only on a whole-suite
    pass, so a failure triggered by content under ``docs/`` prevents a NEW
    receipt from being written.  The consequence: when the framework tree also
    changed, the standing receipt is stale and close is blocked; in a
    documentation-only wave a current green receipt persists and close is not
    blocked despite a red suite.  A green receipt attests the framework code,
    not the tree -- neither a whole-repository guarantee nor a whole-repository
    exemption.

    Where ``run_tests.py`` is absent this is a documented NO-OP that neither
    blocks nor claims proof: ``build_pack.py`` excludes the runner, the tests,
    and the receipt from the distribution under the standing policy that seeds
    must not instruct target repositories to run framework tests, so a
    pack-vendored target can never write the receipt and would otherwise be
    hard-blocked at close forever.
    """
    runner = root / lifecycle_gate_support._FRAMEWORK_TEST_RUNNER_REL
    if not runner.is_file():
        return {"state": "not_applicable", "scope": "framework",
                "detail": (f"`{lifecycle_gate_support._FRAMEWORK_TEST_RUNNER_REL}` is absent (the distribution "
                           "excludes it), so the framework test receipt is not checked here.")}
    # Delivery review REL-DEL-2: `is_file()` follows symlinks, and the runner
    # derives its framework directory and its receipt path from its own RESOLVED
    # location.  A symlinked runner would therefore hash a foreign repository's
    # tree and read a foreign receipt -- a false proof, which is the one direction
    # a gate must never fail in.
    try:
        resolved_runner = runner.resolve()
        resolved_root = root.resolve()
        contained = resolved_runner.is_relative_to(resolved_root)
    except OSError as exc:
        return {"state": "unreadable", "scope": "framework",
                "detail": f"`{lifecycle_gate_support._FRAMEWORK_TEST_RUNNER_REL}` could not be resolved: {exc}"}
    if not contained:
        return {"state": "unreadable", "scope": "framework",
                "detail": (f"`{lifecycle_gate_support._FRAMEWORK_TEST_RUNNER_REL}` resolves outside this repository "
                           f"({resolved_runner}); it would attest a different framework tree, "
                           "so no proof is claimed.")}
    module = lifecycle_gate_support._load_framework_test_runner(runner)
    if module is None or not hasattr(module, "_hash_inputs") or not hasattr(module, "_read_cache"):
        return {"state": "unreadable", "scope": "framework",
                "detail": f"`{lifecycle_gate_support._FRAMEWORK_TEST_RUNNER_REL}` could not be loaded to verify the receipt."}
    # Delivery review REL-DEL-1: the borrowed call CONTRACT can drift too (an
    # older or newer runner whose `_hash_inputs` takes an argument), so both
    # calls degrade to "not proven" rather than raising out of the tool handler.
    try:
        current_hash = module._hash_inputs()
        cached = module._read_cache()
    except (Exception, SystemExit) as exc:  # noqa: BLE001 - any failure here is "not proven"
        return {"state": "unreadable", "scope": "framework",
                "detail": (f"`{lifecycle_gate_support._FRAMEWORK_TEST_RUNNER_REL}` could not verify the receipt "
                           f"({type(exc).__name__}: {exc}).")}
    if not isinstance(cached, dict):
        return {"state": "missing", "scope": "framework",
                "detail": (f"`{lifecycle_gate_support._FRAMEWORK_TEST_RECEIPT_REL}` is absent or unreadable; no "
                           "successful framework test run has been recorded.")}
    if cached.get("result") != "ok":
        return {"state": "not_ok", "scope": "framework", "ran_at": cached.get("ran_at"),
                "detail": (f"`{lifecycle_gate_support._FRAMEWORK_TEST_RECEIPT_REL}` records "
                           f"result={cached.get('result')!r}, not 'ok'.")}
    if cached.get("inputs_hash") != current_hash:
        return {"state": "stale", "scope": "framework", "ran_at": cached.get("ran_at"),
                "test_count": cached.get("test_count"),
                "detail": (f"`{lifecycle_gate_support._FRAMEWORK_TEST_RECEIPT_REL}` was written for a different "
                           "framework tree (a file under `.wavefoundry/framework/` changed "
                           "after that run), so it does not attest the current code.")}
    return {"state": "proven", "scope": "framework", "ran_at": cached.get("ran_at"),
            "test_count": cached.get("test_count"),
            "detail": (f"`{lifecycle_gate_support._FRAMEWORK_TEST_RECEIPT_REL}` is green for the current framework "
                       "tree. It attests the framework code, not the tree: the hash covers "
                       "`.wavefoundry/framework/` only, and the receipt is written only on a "
                       "whole-suite pass.")}
```

### `upgrade_extensions._guard_owned_path`

Class: allowlisted. No resolve by design; lstat refusal of symlinks and Windows reparse points before reading. Follow-up: reconsider only in a separately reviewed contract-specific change.

Source: `.wavefoundry/framework/scripts/upgrade_extensions.py:645`.

Caller/name-reference candidates:
`upgrade_extensions.py:720` `upgrade_extensions.py:730` `upgrade_extensions.py:773` `upgrade_extensions.py:796` `upgrade_extensions.py:857`

Current predicate and failure contract:

```python
def _guard_owned_path(root: Path, path: Path) -> Path:
    """Stdlib-only incoming hook: refuse links before reading checkpoint/source."""
    path.relative_to(root)
    for part in (path, *path.parents):
        if part == root:
            break
        try:
            metadata = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise ValueError("index_guard_checkpoint_invalid: linked recovery/source path")
    return path
```

### `upgrade_wavefoundry._retired_sidecar_path_error`

Class: allowlisted. Deletion-specific existing/missing and canonical wave-root diagnostics. Follow-up: reconsider only in a separately reviewed contract-specific change.

Source: `.wavefoundry/framework/scripts/upgrade_wavefoundry.py:2065`.

Caller/name-reference candidates:
`upgrade_wavefoundry.py:2218`

Current predicate and failure contract:

```python
def _retired_sidecar_path_error(root: Path, candidate: Path) -> str | None:
    """Prove a fixed-name retired sidecar resolves inside the repository.

    Deletion is confined: a symlinked ``docs/waves`` parent or a symlinked
    candidate refuses cleanup, and an outside-root sentinel is left untouched.
    """

    import record_paths  # record roots (wave 1y0gz); lazy like the other sibling imports

    try:
        roots = record_paths.load_record_roots(root)
    except record_paths.RecordLayoutInvalid as exc:
        return str(exc)
    waves_rel = roots.waves_rel
    try:
        root_real = root.resolve(strict=True)
        waves_dir = roots.waves
        if waves_dir.is_symlink():
            return f"{waves_rel} may not be a symlink"
        if not waves_dir.exists():
            return None
        waves_real = waves_dir.resolve(strict=True)
        if not waves_real.is_relative_to(root_real):
            return f"{waves_rel} escapes the repository root"
        if candidate.is_symlink():
            return f"{candidate.name} may not be a symlink"
        if candidate.exists() and not candidate.resolve(strict=True).is_relative_to(
            waves_real
        ):
            return f"{candidate.name} escapes {waves_rel}"
    except (OSError, RuntimeError) as exc:
        return f"retired sidecar path is not safely resolvable: {exc}"
    return None
```

### `review_evidence._review_authority_path_error`

Class: allowlisted. Ledger/member-specific symlink rules and path-free diagnostics. Follow-up: reconsider only in a separately reviewed contract-specific change.

Source: `.wavefoundry/framework/scripts/review_evidence.py:662`.

Caller/name-reference candidates:
`review_evidence.py:4125` `review_evidence.py:4154`

Current predicate and failure contract:

```python
def _review_authority_path_error(wave_path: Path) -> str | None:
    """Reject symlinked/out-of-wave review authority before any read or write."""

    wave_md = Path(wave_path)
    if wave_md.name != "wave.md":
        wave_md = wave_md / "wave.md"
    wave_dir = wave_md.parent
    ledger = wave_dir / EVENTS_FILENAME
    try:
        if wave_dir.is_symlink():
            return "wave directory may not be a symlink"
        wave_real = wave_dir.resolve(strict=True)
        if wave_md.is_symlink():
            return "wave.md may not be a symlink"
        if wave_md.exists() and not wave_md.resolve(strict=True).is_relative_to(wave_real):
            return "wave.md escapes its wave directory"
        if ledger.is_symlink():
            return "events.jsonl may not be a symlink"
        if ledger.exists() and not ledger.resolve(strict=True).is_relative_to(wave_real):
            return "events.jsonl escapes its wave directory"
    except (OSError, RuntimeError) as exc:
        # Path-free (1v1de census): ``OSError.__str__`` and the symlink-loop
        # message both embed the absolute filesystem path, and this string
        # ships to operators through both the ledger-read and validation
        # paths. Name the failing member plus the cause instead.
        cause = getattr(exc, "strerror", None) or type(exc).__name__
        failed_member = getattr(exc, "filename", None)
        if failed_member:
            return (
                "review authority path is not safely resolvable: "
                f"{Path(failed_member).name}: {cause}"
            )
        return f"review authority path is not safely resolvable: {cause}"
    return None
```

### `wave_lint_lib/helpers._is_under`

Class: allowlisted. Lexical no-resolve predicate by design. Follow-up: reconsider only in a separately reviewed contract-specific change.

Source: `.wavefoundry/framework/scripts/wave_lint_lib/helpers.py:83`.

Caller/name-reference candidates:
`wave_lint_lib/helpers.py:113` `wave_lint_lib/helpers.py:106`

Current predicate and failure contract:

```python
def _is_under(path: Path, ancestor: Path) -> bool:
    try:
        path.relative_to(ancestor)
        return True
    except ValueError:
        return False
```

### `repair_ppol_memory_staging.safe`

Class: allowlisted. Owned-boundary lstat walk, reparse rejection and Refused exception contract. Follow-up: reconsider only in a separately reviewed contract-specific change.

Source: `.wavefoundry/framework/scripts/repair_ppol_memory_staging.py:43`.

Caller/name-reference candidates:
`repair_ppol_memory_staging.py:105` `repair_ppol_memory_staging.py:179` `repair_ppol_memory_staging.py:182` `repair_ppol_memory_staging.py:221` `repair_ppol_memory_staging.py:125` `repair_ppol_memory_staging.py:69` `repair_ppol_memory_staging.py:81` `repair_ppol_memory_staging.py:226` `repair_ppol_memory_staging.py:230` `repair_ppol_memory_staging.py:237` `repair_ppol_memory_staging.py:74` `repair_ppol_memory_staging.py:158` `repair_ppol_memory_staging.py:164` `repair_ppol_memory_staging.py:200` `repair_ppol_memory_staging.py:162` `repair_ppol_memory_staging.py:167` `tests/test_repair_ppol_memory_staging.py:204` `tests/test_repair_ppol_memory_staging.py:208`

Current predicate and failure contract:

```python
def safe(path: Path, boundary: Path | None = None) -> Path:
    """Reject redirects inside an owned boundary; allow redirected host ancestors."""
    path = Path(os.path.abspath(path))
    if boundary is None:
        # Explicit locators may live under /tmp aliases or redirected profiles.
        path = path.parent.resolve() / path.name
        boundary = path.parent
    boundary = Path(boundary).resolve()
    try:
        relative = path.relative_to(boundary)
    except ValueError as exc:
        raise Refused(f"Path escapes its ownership boundary: {path}") from exc
    parts = [boundary]
    for name in relative.parts:
        parts.append(parts[-1] / name)
    for part in parts:
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
            raise Refused(f"Redirected path is not supported: {part}")
    return path
```

## Adoption implementation

All ten direct adopters now use `contained_resolved_path` after their original filesystem operations; TechDocs remains indirect through the renderer. The resolving primitive delegates its final comparison to the same pure helper. `server_impl` imports the module at module top and includes it in its reload purge set; other adopters look it up per call so they observe that refreshed module. A modified-scratch real MCP reload test proves the new comparison reaches the server boundary.

`_contained_wave_review_paths` retains the native `relative_to` call only after the pure helper refuses, solely to preserve the original version-specific ValueError cause and diagnostic; it is not a second enforcement decision.

The documented approximate AST census additionally recognizes two non-containment identities: `venv_bootstrap._running_inside_venv` compares interpreter identity, and `build_pack.find_repo_root` terminates ancestor traversal. Tests explicitly name these false positives separately from the nineteen containment exclusions and check for stale entries. All thirty named sites are independently checked for existence/adoption or reasoned exemption.
