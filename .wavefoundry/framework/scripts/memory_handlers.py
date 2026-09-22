"""Memory response handlers; lifecycle compositions remain in server_impl."""
from __future__ import annotations

import contextlib
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Iterable, Optional

from lifecycle_gate_support import _diagnostic
from review_evidence import read_review_event_ledger


# ---------------------------------------------------------------------------
# Agent memory tools (wave 1ro44 / 1p8gy): add / search / brief / reconcile
# ---------------------------------------------------------------------------
#
# The record FILES under docs/agents/memory/ are the source of truth (few,
# small, live); the semantic index is an optional retrieval assist and its
# absence has explicit lexical recovery. Decay is a ranking view, never a mutation.

# Advisory caps (1p8gy Req 6: named constants, response bloat is a hot-path
# concern). A briefing is a nudge, not a document — five entries is what an
# agent actually reads before acting.
MEMORY_BRIEF_CAP = 5
MEMORY_SEARCH_CAP = 20
MEMORY_QUERY_CHECK_CAP = 5
MEMORY_QUERY_MIN_LOGIT = -4.0
MEMORY_PROPOSE_CAP = 20
MEMORY_CONSOLIDATE_GROUP_CAP = 10
MEMORY_CONSOLIDATE_MEMBER_CAP = 5
MEMORY_SUMMARY_EXCERPT_CHARS = 280
MEMORY_BRIEF_CONTEXTS = (
    "session_start", "pre_implementation", "review", "close", "setup", "file_edit",
)


def _memory_mod():
    import server_impl
    return server_impl._load_script("memory_records")


def _memory_fence(root: Path) -> Optional[str]:
    """Register a WRITER-OWNED fence token BEFORE a record filesystem mutation.
    Returns the token on success; None means the caller must REFUSE the mutation
    (an unfenced write could leave another process serving stale). The token
    must be passed to ``_memory_finalize`` so this writer clears ONLY its own
    fence (a concurrent writer's fence must survive)."""
    import server_impl
    try:
        tok = server_impl._load_script("index_state_store").memory_fence(
            root / ".wavefoundry" / "index"
        )
        return tok if isinstance(tok, str) and tok else None
    except Exception:
        return None


def _memory_finalize(root: Path, token: Optional[str] = None) -> None:
    """Remove THIS writer's fence token + advance the generation after a
    mutation, and evict the local cache. Best-effort: if the durable finalize
    fails, the token remains so every process keeps bypassing the cache (no
    stale serve) until the next successful mutation or the TTL self-heals it."""
    import server_impl
    _MEMORY_RECORDS_CACHE.pop(str(root), None)
    try:
        server_impl._load_script("index_state_store").memory_finalize(
            root / ".wavefoundry" / "index", token
        )
    except Exception:
        pass


# Exact lifecycle-id token (v2 scheme): 5-char base36, digit-led, at least one
# letter, bounded by non-alphanumerics so `1abcd` is never found inside
# `1abcde` (delivery-review prefix-collision finding). Mirrors the derivation
# grammar in index_state_store.WAVE_ID_TOKEN.
_LIFECYCLE_ID_TOKEN_RE = re.compile(r"(?<![a-z0-9])(?=[0-9]*[a-z])[0-9][a-z0-9]{4}(?![a-z0-9])")


def _lifecycle_id_tokens(text: str) -> set[str]:
    return set(_LIFECYCLE_ID_TOKEN_RE.findall(str(text).lower()))


# Hot-path caches (delivery-review perf finding): memory advisories fire on
# code_read/code_impact/code_callhierarchy, so re-reading every record file and
# re-decompressing the cluster artifact per call is the wrong cost. Both caches
# are keyed on a cheap on-disk signature and invalidate the instant the backing
# state changes (a memory write bumps the dir signature; a graph rebuild bumps
# the artifact stat). Bounded: one dict entry per repo root.
_MEMORY_RECORDS_CACHE: dict[str, tuple[Any, list[dict[str, Any]]]] = {}
_MEMORY_BETWEENNESS_CACHE: dict[str, tuple[Any, dict[str, float]]] = {}


_MEMORY_KEY_BYPASS = "__bypass__"


def _memory_cache_key(root: Path):
    """Bounded cache key from the durable memory seqlock — NO per-call tree
    walk. One of:
    - ``None`` — the memory root is absent/uncontained (reads → []);
    - ``_MEMORY_KEY_BYPASS`` — the durable state is UNREADABLE or DIRTY (a
      mutation is in flight, or a finalize failed leaving dirty set); the cache
      is bypassed (always reload fresh) so no process serves stale;
    - ``(epoch, generation, dir_mtime_ns)`` — the normal key. The random epoch
      defeats the delete/recreate ABA; the monotonic generation advances on
      every mutation/invalidate across processes; the dir mtime additionally
      catches add/delete/rename.
    """
    import server_impl
    mem = _memory_mod()
    mem_dir = mem.canonical_memory_root(root)
    if mem_dir is None or not mem_dir.is_dir():
        return None
    try:
        dir_mtime = int(mem_dir.stat().st_mtime_ns)
    except OSError:
        return None
    state = server_impl._load_script("index_state_store").read_memory_state(
        root / ".wavefoundry" / "index"
    )
    if state is None or state.get("dirty"):
        return _MEMORY_KEY_BYPASS
    return (str(state.get("epoch", "")), int(state.get("generation", 0)), dir_mtime)


def _memory_records_cached(root: Path, statuses: Optional[Iterable[str]]) -> list[dict[str, Any]]:
    """All parseable records for ``root``, cached on the bounded key.

    Caches the FULL (all-status) set and filters by status in memory. A key
    change reloads; an unreadable generation BYPASSES the cache (fresh load,
    no store); an absent/uncontained dir → [].
    """
    key_sig = _memory_cache_key(root)
    if key_sig is None:
        return []
    load = _memory_mod().load_memory_records

    def _filter(records):
        if statuses is None:
            return list(records)
        wanted = set(statuses)
        return [r for r in records if r["status"] in wanted]

    if key_sig == _MEMORY_KEY_BYPASS:
        return _filter(load(root))  # durable state unavailable — never cache
    key = str(root)
    cached = _MEMORY_RECORDS_CACHE.get(key)
    if cached and cached[0] == key_sig:
        records = cached[1]
    else:
        records = load(root)  # all statuses
        _MEMORY_RECORDS_CACHE[key] = (key_sig, records)
    return _filter(records)


def _memory_betweenness_by_file(root: Path) -> dict[str, float]:
    """Max persisted betweenness per file from the published communities (top-200).

    Wave 1xny6: read from the community rows through the generation-bound
    snapshot. The per-call cache key is the snapshot's community content
    fingerprint, which replaces the retired artifact's ``(mtime_ns, size)`` —
    the same invalidation intent, keyed on content that actually identifies the
    ranking rather than on a file that no longer exists. Graceful absence: {}
    when no communities are published — ranking falls back to decayed
    confidence alone (AC-12 degrade path).
    """
    import server_impl
    try:
        gs = server_impl._graph_snapshot_module()
        snapshot = gs.acquire(root, "project")
    except Exception:
        return {}
    if not snapshot.clusters_present:
        return {}
    art_sig = (snapshot.community_fingerprint, snapshot.community_content_generation)
    key = str(root)
    cached = _MEMORY_BETWEENNESS_CACHE.get(key)
    if cached and cached[0] == art_sig:
        return cached[1]
    try:
        scores: dict[str, float] = {}
        for entry in ((snapshot.clusters or {}).get("betweenness") or {}).get("ranking") or []:
            node_id = str(entry.get("node_id") or "")
            file_part = node_id.split("::", 1)[0]
            score = float(entry.get("score") or 0.0)
            if file_part and score > scores.get(file_part, 0.0):
                scores[file_part] = score
        _MEMORY_BETWEENNESS_CACHE[key] = (art_sig, scores)
        return scores
    except Exception:
        return {}


def _memory_view(record: dict[str, Any], decay: dict[str, Any]) -> dict[str, Any]:
    summary = str(record.get("summary") or "")
    view = {
        "memory_id": record["memory_id"],
        "title": record.get("title"),
        "kind": record["kind"],
        "status": record["status"],
        "confidence": record.get("confidence"),
        "effective_confidence": round(float(decay.get("effective_confidence") or 0.0), 3),
        "decay_basis": decay.get("decay_basis"),
        "summary": summary[:MEMORY_SUMMARY_EXCERPT_CHARS],
        "target_refs": record.get("target_refs") or [],
        "evidence_refs": record.get("evidence_refs") or [],
        "path": str(Path(record["path"]).as_posix()) if record.get("path") else None,
        "created_at": record.get("created_at"),
        "updated_at": record.get("updated_at"),
    }
    for key in (
        "source_event", "validation", "validated_by", "action_delta",
        "validation_rationale", "evidence_verified",
        "current_target_verified", "canonical_overlap", "record_type",
        "archived_at", "archive_reason", "archive_path", "pointer_to",
        "pending_archive",
    ):
        if record.get(key) is not None:
            view[key] = record[key]
    if record.get("superseded_by"):
        view["superseded_by"] = record["superseded_by"]
    if record.get("keywords"):
        view["keywords"] = record["keywords"]
    if decay.get("needs_reverification"):
        view["needs_reverification"] = True
    return view


def _memory_ranked(
    root: Path,
    records: list[dict[str, Any]],
    *,
    relevance_rank_by_id: Optional[dict[str, int]] = None,
    commit_times_override: Optional[dict[str, list[int]]] = None,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Policy-partitioned freshness/relevance ordering.

    Exact-target handling (at caller filters/promotion), base confidence,
    surfaced status, and kind family remain policy boundaries. Adaptive
    effective confidence and optional semantic relevance order only inside
    them; persisted betweenness is the final scored tie-break before memory id.
    Returns ``[(record, decay)]`` best-first.

    Freshness is read ONCE for the whole batch (delivery-review perf finding):
    all file targets across the records are collected and their windowed
    commit timestamps fetched in a single store query, then per-record churn
    is computed in memory — no per-target store open, no per-call cluster
    decompress (betweenness is cached).
    """
    import server_impl
    mem = _memory_mod()
    index_dir = root / ".wavefoundry" / "index"
    betweenness = _memory_betweenness_by_file(root)

    file_targets = {
        ref for r in records for ref in (r.get("target_refs") or [])
        if not ref.startswith(("symbol:", "community:"))
    }
    commit_times: dict[str, list[int]] = {}
    if commit_times_override is not None:
        # Wave 1tis8: an evaluation caller freezes a commit-history snapshot so
        # its scoring is deterministic. It passes that snapshot in EXPLICITLY —
        # it must never rebind the shared `index_state_store.file_commit_times`
        # global, because this server is long-lived and concurrent: overlapping
        # calls restore out of order and leave a frozen subset installed for
        # every later reader.
        commit_times = {
            path: list(times)
            for path, times in commit_times_override.items()
            if path in file_targets
        }
    elif file_targets:
        try:
            commit_times = server_impl._load_script("index_state_store").file_commit_times(
                index_dir, file_targets
            )
        except Exception:
            commit_times = {}

    def _churn_provider(path: str, since_ts: Optional[int]) -> int:
        times = commit_times.get(path)
        if not times:
            return 0
        if since_ts is None:
            return len(times)
        return sum(1 for t in times if t > since_ts)

    def _centrality(record: dict[str, Any]) -> float:
        best = 0.0
        for ref in record.get("target_refs") or []:
            if ref.startswith(("symbol:", "community:")):
                continue
            best = max(best, betweenness.get(ref, 0.0))
        return best

    relevance_ranks = relevance_rank_by_id or {}
    missing_relevance_rank = max(relevance_ranks.values(), default=0) + 1
    scored = []
    for record in records:
        decay = mem.apply_decay(
            record,
            index_dir=index_dir,
            churn_provider=_churn_provider,
            commit_times_by_path=commit_times,
        )
        scored.append((record, decay, _centrality(record)))
    scored.sort(
        key=lambda item: mem.memory_policy_sort_key(
            item[0],
            item[1],
            relevance_rank=relevance_ranks.get(
                item[0]["memory_id"], missing_relevance_rank
            ) if relevance_ranks else 0,
            centrality=item[2],
        )
    )
    return [(record, decay) for record, decay, _c in scored]


# Per-tool advisory cap on hot read tools (1p8gy Req 6): a nudge in a
# response an agent is reading for OTHER content — three entries max.
MEMORY_ADVISORY_CAP = 3


def _memory_advisories_for_path(root: Path, path: str, symbol: str = "") -> list[dict[str, Any]]:
    """Capped active-memory advisories for a file/symbol (1p8gy AC-5).

    Graceful absence everywhere: no memory directory, no matches, or any
    failure → [] and the host tool's response is unchanged. The empty-match
    short-circuit keeps the hot read tools at directory-scan cost; ranking
    (decay + centrality) runs only when something matched.
    """
    try:
        mem = _memory_mod()
        records = _memory_records_cached(root, mem.DEFAULT_SURFACED_STATUSES)
        if not records:
            return []
        matched = [r for r in records if mem.match_targets(r, path=path, symbol=symbol)]
        if not matched:
            return []
        ranked = _memory_ranked(root, matched)
        surfaced = ranked[:MEMORY_ADVISORY_CAP]
        _credit_exploration_avoided_surface(root, surfaced, [path], mem)
        return [_memory_view(r, d) for r, d in surfaced]
    except Exception:
        return []


def _memory_advisories_for_wave(root: Path, wave: dict[str, Any]) -> list[dict[str, Any]]:
    """Capped advisories relevant to a wave (1p8gy AC-6): records whose
    evidence/target refs mention the wave id or an admitted change id, plus
    any fragile_file advisory flagged needs-reverification. Graceful absence.
    """
    try:
        mem = _memory_mod()
        records = _memory_records_cached(root, mem.DEFAULT_SURFACED_STATUSES)
        if not records:
            return []
        # Exact lifecycle-id token matching (delivery-review finding): collect
        # the wave/change id TOKENS and match refs by whole-token equality, so
        # a memory that references `1abcde` never attaches to wave `1abcd` (the
        # old `ident in ref` substring test did). `_lifecycle_id_tokens` finds
        # 5-char digit-led base36 tokens bounded by non-alphanumerics.
        wave_tokens: set[str] = set()
        wave_id = str(wave.get("wave_id") or wave.get("id") or "")
        if wave_id:
            wave_tokens |= _lifecycle_id_tokens(wave_id)
        for change in wave.get("changes") or []:
            cid = str(change.get("id") or change) if not isinstance(change, str) else change
            if cid:
                wave_tokens |= _lifecycle_id_tokens(cid)
        if not wave_tokens:
            return []

        def _mentions_wave(record: dict[str, Any]) -> bool:
            refs = (record.get("evidence_refs") or []) + (record.get("target_refs") or [])
            return any(_lifecycle_id_tokens(ref) & wave_tokens for ref in refs)

        matched = [r for r in records if _mentions_wave(r)]
        ranked = _memory_ranked(root, matched)
        views = [_memory_view(r, d) for r, d in ranked[:MEMORY_ADVISORY_CAP]]
        # Standing fragile-file warnings that need re-verification surface at
        # lifecycle checkpoints even without a wave-id link.
        if len(views) < MEMORY_ADVISORY_CAP:
            seen = {v["memory_id"] for v in views}
            fragile = [r for r in records
                       if r["kind"] == "fragile_file" and r["memory_id"] not in seen]
            for record, decay in _memory_ranked(root, fragile):
                if decay.get("needs_reverification") and len(views) < MEMORY_ADVISORY_CAP:
                    views.append(_memory_view(record, decay))
        surfaced_matched = [
            pair for pair in ranked[:MEMORY_ADVISORY_CAP]
            if pair[0]["memory_id"] in {view["memory_id"] for view in views}
        ]
        _credit_exploration_avoided_surface(
            root, surfaced_matched, sorted(wave_tokens), mem, evidence_match=True
        )
        return views
    except Exception:
        return []


def _credit_exploration_avoided_surface(
    root: Path,
    surfaced_pairs: list,
    target_list: list,
    mem: Any,
    *,
    evidence_match: bool = False,
) -> None:
    """Fail-isolated 1svuk credit for advisories surfaced by memory_brief.

    Telemetry-only: resolves the current OPEN wave and accrues the SEPARATE,
    labeled estimated-exploration-avoided metric grounded in each surfaced
    record's measured ``source_exploration_cost`` (discounted by a bounded
    attribution). Never raises, never changes the advisory output, and never
    touches the measured Context Efficiency total.
    """
    import server_impl
    try:
        # Attribute to the OPEN (active/implementing) wave specifically — not
        # `current_wave`, which returns the first open wave in lifecycle order
        # and can surface a readied (planned) wave that sorts ahead of the
        # implementing one (they coexist under the single-OPEN rule).
        wave = next(
            (w for w in server_impl.list_waves(root) if w.get("status") in ("active", "implementing")),
            None,
        )
        if not wave:
            return
        wave_id = str(wave.get("wave_id") or wave.get("id") or "").strip()
        if not wave_id:
            return
        ea = server_impl._load_script("exploration_avoided")
        items = []
        for record, _decay in surfaced_pairs:
            if evidence_match:
                refs = (
                    list(record.get("evidence_refs") or [])
                    + list(record.get("target_refs") or [])
                )
                matched = bool(target_list) and any(
                    target in _lifecycle_id_tokens(ref)
                    for target in target_list for ref in refs
                )
            else:
                matched = bool(target_list) and any(
                    mem.match_targets(record, path=t) for t in target_list
                )
            if not matched:
                continue
            origin_tokens: set[str] = set()
            for ref in record.get("evidence_refs") or []:
                origin_tokens |= _lifecycle_id_tokens(str(ref))
            items.append({
                "memory_id": record.get("memory_id"),
                "source_origin": (
                    sorted(origin_tokens)[0]
                    if origin_tokens else record.get("memory_id")
                ),
                "source_exploration_cost": record.get("source_exploration_cost"),
                "match_confidence": 1.0,
            })
        context_key = json.dumps(
            sorted({str(target) for target in target_list}),
            ensure_ascii=False,
            separators=(",", ":"),
        )
        ea.credit_surface(
            root, wave_id, items, cited=False, context_key=context_key
        )
    except Exception:
        return


def memory_add_response(
    root: Path,
    kind: str,
    summary: str,
    evidence: list,
    targets: list,
    title: str = "",
    confidence: float = 0.6,
    status: str = "candidate",
    supersedes: str = "",
    memory_id: str = "",
    abort_if_duplicate: bool = False,
) -> dict[str, Any]:
    """Validate without mutation, then serialize duplicate scan + write."""
    return _memory_add_response_locked(
        root, kind, summary, evidence, targets, title=title,
        confidence=confidence, status=status, supersedes=supersedes,
        memory_id=memory_id, abort_if_duplicate=abort_if_duplicate,
    )


def _memory_add_response_locked(
    root: Path,
    kind: str,
    summary: str,
    evidence: list,
    targets: list,
    title: str = "",
    confidence: float = 0.6,
    status: str = "candidate",
    supersedes: str = "",
    memory_id: str = "",
    abort_if_duplicate: bool = False,
    _lock_held: bool = False,
    _source_event: str = "",
    _validation: str = "",
    _validated_by: str = "",
    _action_delta: str = "",
    _validation_rationale: str = "",
    _evidence_verified: Optional[bool] = None,
    _current_target_verified: Optional[bool] = None,
    _canonical_overlap: str = "",
    _defer_index_refresh: bool = False,
    _source_exploration_cost: Optional[int] = None,
) -> dict[str, Any]:
    import server_impl
    mem = _memory_mod()
    problems: list[str] = []
    kind = (kind or "").strip()
    status = (status or "candidate").strip()
    evidence = [str(e).strip() for e in (evidence or []) if str(e).strip()]
    targets = [str(t).strip() for t in (targets or []) if str(t).strip()]
    if kind not in mem.MEMORY_KINDS:
        problems.append(f"unknown kind {kind!r}; allowed: {', '.join(mem.MEMORY_KINDS)}")
    if status not in ("candidate", "active"):
        problems.append("new records start as 'candidate' or 'active' — other statuses are reconciliation outcomes")
    if not (summary or "").strip():
        problems.append("summary is required (the lesson, phrased as what changes the next action)")
    if not evidence:
        problems.append("evidence refs are required — memory without evidence is opinion")
    if not targets:
        problems.append("target refs are required — an advisory needs something to attach to")
    try:
        confidence = float(confidence)
        if not 0.0 <= confidence <= 1.0:
            raise ValueError
    except (TypeError, ValueError):
        problems.append("confidence must be a number in [0.0, 1.0]")
    # Security boundary (delivery-review finding 2026-07-13): ids are path
    # components — validate caller-supplied ids and supersedes references
    # against the memory-id grammar BEFORE any filesystem access.
    for label, value in (("memory_id", memory_id), ("supersedes", supersedes)):
        if value:
            try:
                mem.validate_memory_id(value)
            except ValueError as exc:
                problems.append(f"{label}: {exc}")
    # Forbidden-content pre-write scan (1p8gy Req 8). Delivery-review finding:
    # scan EVERY caller-controlled field that gets persisted (title + summary +
    # evidence + targets), and NEVER echo the rejected line — the diagnostic
    # names the offending field only, so a secret is not repeated back into
    # logs/responses.
    try:
        from wave_lint_lib.constants import MEMORY_DISALLOWED_PATTERNS as _FORBIDDEN
    except ImportError:
        _FORBIDDEN = ()
    _scanned_fields = (
        ("title", [title or ""]),
        ("summary", [summary or ""]),
        ("evidence", list(evidence)),
        ("targets", list(targets)),
    )
    _forbidden_fields: list[str] = []
    for field_name, chunks in _scanned_fields:
        hit = False
        for chunk in chunks:
            for line in str(chunk).splitlines():
                if any(p.search(line) for p in _FORBIDDEN):
                    hit = True
                    break
            if hit:
                break
        if hit:
            _forbidden_fields.append(field_name)
    if _forbidden_fields:
        problems.append(
            "content looks like a secret, raw transcript, or personal fact in "
            f"{', '.join(_forbidden_fields)} — forbidden by the memory schema "
            "(the offending text is not echoed back)"
        )
    if problems:
        return server_impl._response(
            "error",
            {"written": False, "problems": problems},
            diagnostics=[_diagnostic(
                "invalid_memory_record", "; ".join(problems),
                recovery_tools=["memory_add"],
                recovery_usage="memory_add(kind='fragile_file', summary=..., evidence=[...], targets=[...])",
            )],
            next_tools=["memory_add"],
            usage="",
        )
    if not _lock_held:
        with server_impl.project_state_publication_lock(root):
            return _memory_add_response_locked(
                root, kind, summary, evidence, targets, title=title,
                confidence=confidence, status=status, supersedes=supersedes,
                memory_id=memory_id, abort_if_duplicate=abort_if_duplicate,
                _lock_held=True,
                _source_event=_source_event, _validation=_validation,
                _validated_by=_validated_by, _action_delta=_action_delta,
                _validation_rationale=_validation_rationale,
                _evidence_verified=_evidence_verified,
                _current_target_verified=_current_target_verified,
                _canonical_overlap=_canonical_overlap,
                _defer_index_refresh=_defer_index_refresh,
                _source_exploration_cost=_source_exploration_cost,
            )
    explicit = bool(memory_id)
    base_id = memory_id or mem.mint_memory_id(root, title or summary)

    # Duplicate detection (wave 1stwl) — DETECTION ONLY. Compare a pseudo-record
    # of this add against existing active/candidate records. Non-blocking by
    # default (the record is still written and a possible_duplicate advisory is
    # attached); with abort_if_duplicate the write is refused without mutating
    # anything. Detection never marks superseded/merges/deletes.
    _dup_matches = mem.find_duplicates(
        {"memory_id": memory_id or "", "kind": kind, "summary": summary,
         "evidence_refs": list(evidence), "target_refs": list(targets),
         "status": status},
        mem.load_memory_records(root, statuses=("active", "candidate")),
    )

    def _dup_phrase() -> str:
        return ", ".join(
            f"{m['memory_id']} ({'/'.join(m['signals'])})" for m in _dup_matches
        )

    if _dup_matches and abort_if_duplicate:
        return server_impl._response(
            "error", {"written": False, "duplicates": _dup_matches},
            diagnostics=[_diagnostic(
                "possible_duplicate",
                "Refused: possible duplicate of " + _dup_phrase()
                + " (abort_if_duplicate=True; nothing was written or changed).",
                recovery_tools=["memory_search", "memory_add"],
                recovery_usage="memory_add(..., abort_if_duplicate=False) to write anyway")],
            next_tools=["memory_search"], usage="",
        )

    # Wave 1tdl8: a successor record inherits the superseded record's measured
    # `source_exploration_cost` — the grounding exploration is shared by
    # construction through the explicit supersession link (this covers both
    # memory_validate rewrites and hand-authored memory_add(supersedes=...)).
    # An explicitly provided cost wins over inheritance. Inheritance never
    # stamps a record without supersession lineage, and only a POSITIVE
    # measured cost is carried (zero grounds nothing).
    _inherited_cost: Optional[int] = _source_exploration_cost
    if _inherited_cost is None and supersedes:
        try:
            _prior_record = mem.parse_memory_record(
                mem._contained_record_path(root, supersedes)
            )
            _prior_cost = (
                _prior_record.get("source_exploration_cost")
                if _prior_record
                else None
            )
            if _prior_cost is not None and int(_prior_cost) > 0:
                _inherited_cost = int(_prior_cost)
        except (OSError, ValueError):
            _inherited_cost = None

    def _render(mid: str) -> str:
        return mem.render_memory_record(
            memory_id=mid, kind=kind, summary=summary, evidence=evidence,
            targets=targets, title=title, confidence=confidence, status=status,
            supersedes=supersedes,
            source_event=_source_event, validation=_validation,
            validated_by=_validated_by, action_delta=_action_delta,
            validation_rationale=_validation_rationale,
            evidence_verified=_evidence_verified,
            current_target_verified=_current_target_verified,
            canonical_overlap=_canonical_overlap,
            source_exploration_cost=_inherited_cost,
        )

    # Fence the durable seqlock BEFORE any filesystem write (delivery-review
    # round 4): if the fence cannot be established, refuse the mutation — an
    # unfenced write could leave a second MCP process serving a stale advisory.
    # The token is writer-owned; finalize clears ONLY this token.
    _fence_token = _memory_fence(root)
    if _fence_token is None:
        return server_impl._response(
            "error", {"written": False},
            diagnostics=[_diagnostic(
                "memory_state_unwritable",
                "Cannot establish the memory-state fence (memory-state.sqlite is "
                "unwritable). Refusing the write so no process serves a stale advisory.",
                recovery_tools=["memory_add"], recovery_usage="")],
            next_tools=["memory_add"], usage="",
        )
    diagnostics: list[dict[str, Any]] = []
    if _dup_matches:
        diagnostics.append(_diagnostic(
            "possible_duplicate",
            "Written as requested, but this record possibly duplicates "
            + _dup_phrase() + " — detection only; reconcile explicitly if it is "
            "a duplicate (nothing was auto-superseded or merged).",
            recovery_tools=["memory_search", "memory_reconcile"],
            recovery_usage="memory_search(target=...) to compare"))
    try:
        # Atomic creation: exclusive-create, retry only generated-id
        # collisions, surface the conflict for an explicit id. No TOCTOU.
        try:
            path, memory_id = mem.create_memory_record(root, _render, base_id, explicit=explicit)
        except ValueError as exc:
            return server_impl._response(
                "error", {"written": False},
                diagnostics=[_diagnostic("invalid_memory_record", str(exc),
                                         recovery_tools=["memory_add"],
                                         recovery_usage="memory_add(memory_id='mem-<kebab-slug>', ...)")],
                next_tools=["memory_add"], usage="",
            )
        except FileExistsError as exc:
            return server_impl._response(
                "error", {"written": False},
                diagnostics=[_diagnostic("memory_record_exists", str(exc),
                                         recovery_tools=["memory_reconcile"],
                                         recovery_usage=f"memory_reconcile(memory_id={base_id!r}, status='superseded', superseded_by=<new id>)")],
                next_tools=["memory_search"], usage="",
            )
        if supersedes:
            try:
                mem.reconcile_memory_record(root, supersedes, "superseded", superseded_by=memory_id)
            except (FileNotFoundError, ValueError) as exc:
                diagnostics.append(_diagnostic(
                    "supersedes_target_not_updated",
                    f"The new record was written but {supersedes!r} could not be marked superseded: {exc}",
                    recovery_tools=["memory_reconcile"],
                    recovery_usage=f"memory_reconcile(memory_id={supersedes!r}, status='superseded', superseded_by={memory_id!r})",
                ))
    finally:
        # Clear THIS writer's fence + advance the generation. A concurrent
        # writer's fence survives (only our token is removed).
        _memory_finalize(root, _fence_token)
    if not _defer_index_refresh:
        server_impl._trigger_background_index_refresh_for_paths(root, [path])
    record = mem.parse_memory_record(path)
    decay = mem.apply_decay(record, index_dir=root / ".wavefoundry" / "index") if record else {}
    return server_impl._response(
        "ok",
        {"written": True, "record": _memory_view(record, decay) if record else {"memory_id": memory_id}},
        diagnostics=diagnostics,
        next_tools=["memory_search", "memory_brief"],
        usage=f"memory_search(target={targets[0]!r})",
    )


def _draft_view(d: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": d["kind"], "title": d["title"], "summary": d["summary"],
        "evidence": list(d["evidence"]), "targets": list(d["targets"]),
        "source_event": d["source_event"],
        "source_exploration_cost": d["source_exploration_cost"],
    }


def memory_propose_response(
    root: Path,
    wave_id: str = "",
    mode: str = "dry_run",
    limit: int = MEMORY_PROPOSE_CAP,
    *,
    _defer_index_refresh: bool = False,
) -> dict[str, Any]:
    """Serialize create-mode duplicate scan + batch write as one operation."""
    import server_impl
    lock = (
        server_impl.project_state_publication_lock(root)
        if (mode or "").strip() == "create"
        else contextlib.nullcontext()
    )
    with lock:
        return _memory_propose_response_locked(
            root,
            wave_id=wave_id,
            mode=mode,
            limit=limit,
            defer_index_refresh=_defer_index_refresh,
        )


def _memory_propose_response_locked(
    root: Path,
    wave_id: str = "",
    mode: str = "dry_run",
    limit: int = MEMORY_PROPOSE_CAP,
    *,
    defer_index_refresh: bool = False,
) -> dict[str, Any]:
    """Draft candidate memory records from a wave's typed review evidence.

    Reads the wave's ``events.jsonl`` heads + admitted change-doc Decision Logs
    and drafts durable-shaped ``candidate`` records (never auto-promoted).
    ``dry_run`` (default) returns the drafts; ``create`` writes them through the
    existing candidate write path, skipping exact/normalized duplicates so
    re-runs are idempotent (1stwl detector). Local-only, read-then-draft.
    """
    import server_impl
    mem = _memory_mod()
    supply = server_impl._load_script("memory_supply")
    wave_id = (wave_id or "").strip()
    mode = (mode or "dry_run").strip()
    if mode not in ("dry_run", "create"):
        return server_impl._response(
            "error", {"valid_modes": ["dry_run", "create"]},
            diagnostics=[_diagnostic(
                "invalid_arguments", f"unknown mode {mode!r}; use 'dry_run' or 'create'",
                recovery_tools=["memory_propose"],
                recovery_usage="memory_propose(wave_id='<id>', mode='dry_run')")],
            next_tools=["memory_propose"], usage="")
    if not wave_id:
        return server_impl._response(
            "error", {"proposed": []},
            diagnostics=[_diagnostic(
                "invalid_arguments", "provide a wave_id to draft memory candidates from",
                recovery_tools=["wf_current_wave", "memory_propose"],
                recovery_usage="memory_propose(wave_id='<id>')")],
            next_tools=["wf_current_wave"], usage="")
    try:
        n = max(1, min(int(limit), MEMORY_PROPOSE_CAP))
    except (TypeError, ValueError):
        n = MEMORY_PROPOSE_CAP
    _wave_dir, wave_error = supply.resolve_wave_dir(root, wave_id)
    if wave_error:
        return server_impl._response(
            "error",
            {"proposed": [], "records_proposed": 0, "records_promoted": 0,
             "records_written": 0},
            diagnostics=[_diagnostic(
                wave_error,
                "Wave id is ambiguous." if wave_error == "ambiguous_wave_id"
                else "Wave was not found.",
                recovery_tools=["wf_list_waves", "memory_propose"],
                recovery_usage="wf_list_waves()")],
            next_tools=["wf_list_waves"], usage="")
    # Read the complete eligible set, then page AFTER suppressing durable
    # dispositions. Otherwise the first 20 already-validated sources would
    # permanently hide source 21+ on every subsequent run.
    drafts = supply.draft_candidates(root, wave_id, limit=None)

    # Idempotent supply (AC-5): skip a draft whose (kind, targets, normalized
    # summary) already exists (existing corpus + earlier in this run). The
    # shared wave-id evidence ref is deliberately NOT a skip reason — every
    # same-wave draft carries it — so dedup keys on normalized_content only.
    accumulated = list(mem.load_memory_records(root))
    disposition_sources = {
        str(record.get("source_event") or "")
        for record in accumulated
        if record.get("source_event")
    }
    try:
        purged_source_digests = mem.load_purged_source_event_digests(root)
    except (ValueError, OSError):
        return server_impl._response(
            "error",
            {"proposed": [], "records_proposed": 0, "records_promoted": 0,
             "records_written": 0},
            diagnostics=[_diagnostic(
                "memory_disposition_authority_unreadable",
                "Cannot read the repo-visible purged-source authority; proposal refused to avoid regenerating finalized history.",
                recovery_tools=["memory_propose"],
                recovery_usage="repair or restore .wavefoundry/memory-purge-dispositions.json, then retry",
            )],
            next_tools=["memory_propose"],
            usage="",
        )
    unique: list[dict[str, Any]] = []
    eligible_count = 0
    skipped_duplicates = 0
    skipped_dispositions = 0
    for d in drafts:
        if (
            d["source_event"] in disposition_sources
            or mem.source_event_digest(d["source_event"]) in purged_source_digests
        ):
            skipped_dispositions += 1
            continue
        pseudo = {"memory_id": "", "kind": d["kind"], "summary": d["summary"],
                  "evidence_refs": list(d["evidence"]), "target_refs": list(d["targets"]),
                  "status": "candidate"}
        matches = mem.find_duplicates(pseudo, accumulated)
        if any("normalized_content" in m["signals"] for m in matches):
            skipped_duplicates += 1
            continue
        eligible_count += 1
        if len(unique) < n:
            unique.append(d)
        # Continue tracking the complete eligible set after the response page
        # fills. This lets the coordinator distinguish an exactly-full final
        # page from a page with additional durable sources without returning
        # those source bodies.
        accumulated.append(pseudo)
        disposition_sources.add(d["source_event"])

    if not drafts:
        return server_impl._response(
            "ok",
            {"proposed": [], "records_proposed": 0, "records_promoted": 0,
             "records_written": 0,
             "skipped_duplicates": 0, "skipped_dispositions": 0, "mode": mode},
            diagnostics=[_diagnostic(
                "no_material_evidence",
                "No durable-shaped evidence to draft from this wave (Decision Logs "
                "with a code anchor, or repaired real-defect findings). Sparse by design.",
                recovery_tools=["memory_propose"], recovery_usage="")],
            next_tools=["memory_search"], usage="")

    if mode == "dry_run":
        return server_impl._response(
            "ok",
            {"proposed": [_draft_view(d) for d in unique],
             "records_proposed": len(unique), "records_promoted": 0,
             "records_written": 0,
             "records_remaining": max(0, eligible_count - len(unique)),
             "exhausted": eligible_count <= len(unique),
             "skipped_duplicates": skipped_duplicates,
             "skipped_dispositions": skipped_dispositions, "mode": "dry_run"},
            diagnostics=[], next_tools=["memory_propose"],
            usage=f"memory_propose(wave_id={wave_id!r}, mode='create')")

    # create: fence the seqlock, then write each unique draft as a candidate.
    try:
        from wave_lint_lib.constants import MEMORY_DISALLOWED_PATTERNS as _FORBIDDEN
    except ImportError:
        _FORBIDDEN = ()
    _fence_token = _memory_fence(root)
    if _fence_token is None:
        return server_impl._response(
            "error", {"written": []},
            diagnostics=[_diagnostic(
                "memory_state_unwritable",
                "Cannot establish the memory-state fence; refusing the batch write.",
                recovery_tools=["memory_propose"], recovery_usage="")],
            next_tools=["memory_propose"], usage="")
    written: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    try:
        for d in unique:
            fields = [d["summary"], d["title"], *d["evidence"], *d["targets"]]
            if any(p.search(line) for f in fields
                   for line in str(f).splitlines() for p in _FORBIDDEN):
                diagnostics.append(_diagnostic(
                    "memory_draft_skipped_forbidden",
                    f"A draft from {d['source_event']} was skipped: content matched a "
                    "forbidden pattern (not echoed).",
                    recovery_tools=[], recovery_usage=""))
                continue
            base_id = mem.mint_memory_id(root, d["title"] or d["summary"])

            def _render(mid: str, _d: dict[str, Any] = d) -> str:
                return mem.render_memory_record(
                    memory_id=mid, kind=_d["kind"], summary=_d["summary"],
                    evidence=list(_d["evidence"]), targets=list(_d["targets"]),
                    title=_d["title"], status="candidate",
                    source_exploration_cost=_d["source_exploration_cost"],
                    source_event=_d["source_event"], validation="pending")

            try:
                path, mid = mem.create_memory_record(root, _render, base_id, explicit=False)
                written.append({
                    "memory_id": mid, "kind": d["kind"],
                    "path": str(path.relative_to(root)).replace("\\", "/"),
                    "source_event": d["source_event"]})
            except (ValueError, FileExistsError, OSError) as exc:
                diagnostics.append(_diagnostic(
                    "memory_draft_write_failed",
                    f"A draft from {d['source_event']} could not be written: {exc}",
                    recovery_tools=[], recovery_usage=""))
    finally:
        _memory_finalize(root, _fence_token)
    if written and not defer_index_refresh:
        server_impl._trigger_background_index_refresh_for_paths(root, [root / w["path"] for w in written])
    return server_impl._response(
        "ok",
        {"proposed": [_draft_view(d) for d in unique], "written": written,
         "records_proposed": len(unique), "records_promoted": 0,
         "records_written": len(written),
         "records_remaining": max(0, eligible_count - len(unique)),
         "exhausted": eligible_count <= len(unique),
         "skipped_duplicates": skipped_duplicates,
         "skipped_dispositions": skipped_dispositions, "mode": "create"},
        diagnostics=diagnostics,
        next_tools=["memory_validate", "memory_search"],
        usage="memory_validate(memory_id=<id>, verdict='promote', action_delta=..., rationale=..., evidence_verified=True, current_target_verified=True, canonical_overlap='none')")


def memory_backfill_response(
    root: Path,
    mode: str = "dry_run",
    limit: int = 20,
    *,
    entry_path: str = "manual",
) -> dict[str, Any]:
    """Inventory and mechanically draft one bounded historical-memory batch."""
    import server_impl

    backfill = server_impl._load_script("memory_backfill")
    mode_s = str(mode or "dry_run").strip().lower()
    if mode_s not in {"dry_run", "create"}:
        return server_impl._response(
            "error",
            {"mode": mode_s},
            diagnostics=[_diagnostic("invalid_arguments", "mode must be dry_run or create")],
            next_tools=["memory_backfill"],
        )
    entry_path_s = str(entry_path or "manual").strip().lower()
    if entry_path_s not in backfill.ENTRY_PATHS:
        return server_impl._response(
            "error",
            {
                "valid_entry_paths": sorted(backfill.ENTRY_PATHS),
            },
            diagnostics=[
                _diagnostic(
                    "invalid_arguments",
                    "entry_path must be manual, setup, or upgrade",
                )
            ],
            next_tools=["memory_backfill"],
        )
    try:
        candidate_budget = max(1, min(int(limit), backfill.MAX_CANDIDATES_PER_CALL))
    except (TypeError, ValueError):
        candidate_budget = backfill.MAX_CANDIDATES_PER_CALL
    try:
        inventory = backfill.inventory_closed_waves(root)
    except OSError as exc:
        return server_impl._response(
            "error",
            {"mode": mode_s, "entry_path": entry_path_s},
            diagnostics=[
                _diagnostic(
                    "historical_memory_inventory_failed",
                    f"Historical wave inventory was refused: {exc}",
                    recovery_tools=["memory_backfill"],
                    recovery_usage="repair the local docs/waves path, then retry",
                )
            ],
            next_tools=["memory_backfill"],
        )
    if mode_s == "dry_run":
        return server_impl._response(
            "dry_run",
            {
                "mode": mode_s,
                "entry_path": entry_path_s,
                "eligible_waves": sum(
                    1 for item in inventory if item["status"] in backfill._CLOSED_STATES
                ),
                "unsupported_waves": sum(
                    1 for item in inventory if item["status"] == "unsupported"
                ),
                "unreadable_waves": sum(
                    1 for item in inventory if item["status"] == "unreadable"
                ),
                "limits": {
                    "waves": backfill.MAX_WAVES_PER_CALL,
                    "candidates": candidate_budget,
                    "response_bytes": backfill.MAX_RESPONSE_BYTES,
                },
            },
            next_tools=["memory_backfill"],
            usage="memory_backfill(mode='create')",
        )

    processed: list[dict[str, Any]] = []
    with server_impl.project_state_publication_lock(root):
        run_id = backfill.ensure_run(root, entry_path_s)
        backfill.sync_inventory(root, run_id, inventory=inventory)
        processed, summary, worklist = _memory_backfill_batch_locked(
            root,
            backfill=backfill,
            run_id=run_id,
            candidate_budget=candidate_budget,
        )
    payload = {
        **summary,
        **worklist,
        "mode": "create",
        "processed": processed,
        "limits": {
            "waves": backfill.MAX_WAVES_PER_CALL,
            "candidates": min(
                int(limit) if isinstance(limit, int) else backfill.MAX_CANDIDATES_PER_CALL,
                backfill.MAX_CANDIDATES_PER_CALL,
            ),
            "response_bytes": backfill.MAX_RESPONSE_BYTES,
        },
    }
    if len(json.dumps(payload, ensure_ascii=False).encode("utf-8")) > backfill.MAX_RESPONSE_BYTES:
        payload["processed"] = [
            {
                key: (
                    str(value)[:2048]
                    if key in {"error", "message"}
                    else value
                )
                for key, value in row.items()
            }
            for row in processed[:1]
        ]
        payload["last_failure"] = str(payload.get("last_failure") or "")[:2048]
        payload["response_truncated"] = True
    if len(json.dumps(payload, ensure_ascii=False).encode("utf-8")) > backfill.MAX_RESPONSE_BYTES:
        # Retain the run-level state/census contract and drop only per-wave
        # presentation detail. Candidate bodies never appear in this response.
        payload["processed"] = []
        payload["last_failure"] = str(payload.get("last_failure") or "")[:256]
    if summary["state"] == "awaiting_validation":
        next_tools = ["memory_validate", "memory_backfill"]
        usage = (
            "validate each data.validation_worklist[].memory_id, then call "
            "memory_backfill(mode='create') for the next exact page"
        )
    elif entry_path_s == "upgrade":
        next_tools = ["wf_upgrade"]
        usage = "wf_upgrade(phase='resume_after_memory')"
    elif entry_path_s == "setup":
        next_tools = []
        usage = "Rerun ordinary `wf setup`; it resumes the durable setup run."
    else:
        next_tools = []
        usage = "Historical memory validation is complete."
    return server_impl._response(
        "ok",
        payload,
        diagnostics=[],
        next_tools=next_tools,
        usage=usage,
    )


def _memory_backfill_batch_locked(
    root: Path,
    *,
    backfill: Any,
    run_id: str,
    candidate_budget: int,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    """Process one bounded historical-memory batch while publication is held.

    The public ``memory_backfill`` wrapper and the protocol-2 upgrade runner
    share this exact producer path.  The upgrade may therefore auto-advance a
    no-judgment batch without inventing a second extractor or treating an
    initially empty validation page as proof that no work exists.
    """
    import server_impl

    processed: list[dict[str, Any]] = []
    remaining_budget = max(
        1,
        min(int(candidate_budget), backfill.MAX_CANDIDATES_PER_CALL),
    )
    for _ in range(backfill.MAX_WAVES_PER_CALL):
        if remaining_budget <= 0:
            break
        claim = backfill.claim_next(root, run_id)
        if claim is None:
            break
        wave_id = claim["wave_id"]
        try:
            proposed = _memory_propose_response_locked(
                root,
                wave_id=wave_id,
                mode="create",
                limit=remaining_budget,
                defer_index_refresh=True,
            )
            if proposed.get("status") != "ok":
                message = "; ".join(
                    str(item.get("message") or item.get("code") or "backfill failed")
                    for item in proposed.get("diagnostics", [])
                )
                backfill.fail_claim(
                    root, run_id, wave_id, claim["claim_token"], message
                )
                processed.append(
                    {"wave_id": wave_id, "outcome": "failed", "error": message}
                )
                continue
            data = proposed.get("data", {})
            count = int(data.get("records_written") or 0)
            draft_write_failures = [
                item
                for item in proposed.get("diagnostics", [])
                if item.get("code")
                in {"memory_draft_skipped_forbidden", "memory_draft_write_failed"}
            ]
            if draft_write_failures:
                message = "; ".join(
                    str(item.get("message") or item.get("code"))
                    for item in draft_write_failures
                )
                backfill.fail_claim(
                    root, run_id, wave_id, claim["claim_token"], message
                )
                processed.append(
                    {"wave_id": wave_id, "outcome": "failed", "error": message}
                )
                continue
            no_source = any(
                item.get("code") == "no_material_evidence"
                for item in proposed.get("diagnostics", [])
            )
            supply = server_impl._load_script("memory_supply")
            wave_dir, _wave_error = supply.resolve_wave_dir(root, wave_id)
            ledger_errors: tuple[str, ...] = ()
            if wave_dir is not None:
                _ledger_rows, ledger_errors = read_review_event_ledger(wave_dir)
            if no_source and ledger_errors:
                outcome = "unsupported"
            else:
                outcome = "no_source" if no_source else "extracted"
            exhausted = no_source or bool(data.get("exhausted"))
            source_records = list(data.get("written") or ())
            # Crash recovery: a previous attempt may have committed the
            # candidate file but died before completing the SQLite claim.
            # Recover stable source identities from the current record
            # corpus so the pending-validation census cannot go false-zero.
            if wave_dir is not None:
                source_events = {
                    str(draft.get("source_event") or "")
                    for draft in supply.draft_candidates(root, wave_id, limit=None)
                }
                for record in _memory_mod().load_memory_records(root):
                    if str(record.get("source_event") or "") in source_events:
                        source_records.append(
                            {
                                "source_event": record.get("source_event"),
                                "memory_id": record.get("memory_id"),
                            }
                        )
            backfill.complete_claim(
                root,
                run_id,
                wave_id,
                claim["claim_token"],
                outcome=outcome,
                candidate_count=count,
                source_records=source_records,
                exhausted=exhausted,
            )
            remaining_budget -= count
            processed.append(
                {
                    "wave_id": wave_id,
                    "outcome": outcome,
                    "candidates_written": count,
                    "exhausted": exhausted,
                }
            )
        except Exception as exc:  # noqa: BLE001 — persist exact failed wave
            backfill.fail_claim(
                root, run_id, wave_id, claim["claim_token"], str(exc)
            )
            processed.append(
                {"wave_id": wave_id, "outcome": "failed", "error": str(exc)}
            )
    summary = backfill.run_summary(root, run_id)
    worklist = backfill.validation_worklist(
        root, run_id, limit=backfill.MAX_CANDIDATES_PER_CALL
    )
    return processed, summary, worklist


def _memory_file_target_exists(root: Path, target: str) -> bool:
    """Best-effort current-tree proof for a file target; symbols are agent-verified."""
    target = str(target or "").strip().strip("`")
    if not target or target.startswith(("symbol:", "community:")):
        return True
    direct = root / target
    if direct.is_file():
        return True
    name = Path(target).name
    if not name:
        return False
    try:
        return any(
            path.is_file()
            and str(path.relative_to(root)).replace("\\", "/").endswith(target)
            for path in root.rglob(name)
        )
    except OSError:
        return False


def memory_validate_response(
    root: Path,
    memory_id: str,
    verdict: str,
    action_delta: str,
    rationale: str,
    evidence_verified: bool,
    current_target_verified: bool,
    canonical_overlap: str,
    *,
    rewrite_kind: str = "",
    rewrite_title: str = "",
    rewrite_summary: str = "",
    rewrite_evidence: Optional[list] = None,
    rewrite_targets: Optional[list] = None,
    rewrite_confidence: float = 0.8,
) -> dict[str, Any]:
    """Record a focused agent judgment over one evidence-derived candidate."""
    import server_impl
    mem = _memory_mod()
    memory_id = str(memory_id or "").strip()
    verdict = str(verdict or "").strip()
    canonical_overlap = str(canonical_overlap or "").strip()
    problems: list[str] = []
    try:
        mem.validate_memory_id(memory_id)
    except ValueError as exc:
        problems.append(str(exc))
    if verdict not in ("promote", "retain", "reject", "rewrite"):
        problems.append("verdict must be promote, retain, reject, or rewrite")
    if canonical_overlap not in ("none", "supplements", "duplicates"):
        problems.append("canonical_overlap must be none, supplements, or duplicates")
    for label, value in (("action_delta", action_delta), ("rationale", rationale)):
        value = str(value or "")
        if not value.strip() or any(c in value for c in ("\r", "\n")):
            problems.append(f"{label} must be a non-empty single line")
    if verdict in ("promote", "retain", "rewrite"):
        if not evidence_verified:
            problems.append(f"{verdict} requires evidence_verified=True")
        if not current_target_verified:
            problems.append(f"{verdict} requires current_target_verified=True")
        if canonical_overlap == "duplicates":
            problems.append(
                f"{verdict} cannot duplicate a canonical contract; reject the draft"
            )
    rewrite_evidence = [
        str(value).strip() for value in (rewrite_evidence or []) if str(value).strip()
    ]
    rewrite_targets = [
        str(value).strip() for value in (rewrite_targets or []) if str(value).strip()
    ]
    if verdict == "rewrite":
        if rewrite_kind not in mem.MEMORY_KINDS:
            problems.append(f"rewrite_kind must be one of {', '.join(mem.MEMORY_KINDS)}")
        if not str(rewrite_summary or "").strip():
            problems.append("rewrite_summary is required for rewrite")
        if not rewrite_evidence:
            problems.append("rewrite_evidence is required for rewrite")
        if not rewrite_targets:
            problems.append("rewrite_targets is required for rewrite")
        try:
            rewrite_confidence = float(rewrite_confidence)
            if not 0.0 <= rewrite_confidence <= 1.0:
                raise ValueError
        except (TypeError, ValueError):
            problems.append("rewrite_confidence must be a number in [0.0, 1.0]")
    # Every caller-controlled field that can reach the record must pass the
    # same pre-write forbidden-content boundary as memory_add. Report only
    # field names so rejected secrets never echo into responses or logs.
    try:
        from wave_lint_lib.constants import MEMORY_DISALLOWED_PATTERNS as _FORBIDDEN
    except ImportError:
        _FORBIDDEN = ()
    validation_fields = (
        ("action_delta", [action_delta]),
        ("rationale", [rationale]),
        ("rewrite_title", [rewrite_title]),
        ("rewrite_summary", [rewrite_summary]),
        ("rewrite_evidence", rewrite_evidence),
        ("rewrite_targets", rewrite_targets),
    )
    forbidden_fields: list[str] = []
    for field_name, chunks in validation_fields:
        if any(
            pattern.search(line)
            for chunk in chunks
            for line in str(chunk).splitlines()
            for pattern in _FORBIDDEN
        ):
            forbidden_fields.append(field_name)
    if forbidden_fields:
        problems.append(
            "content looks like a secret, raw transcript, or personal fact in "
            f"{', '.join(forbidden_fields)} — forbidden by the memory schema "
            "(the offending text is not echoed back)"
        )
    if problems:
        return server_impl._response(
            "error", {"validated": False, "problems": problems},
            diagnostics=[_diagnostic(
                "invalid_memory_validation", "; ".join(problems),
                recovery_tools=["memory_validate"], recovery_usage="")],
            next_tools=["memory_validate"], usage="")

    with server_impl.project_state_publication_lock(root):
        records = {record["memory_id"]: record for record in mem.load_memory_records(root)}
        record = records.get(memory_id)
        if record is None:
            return server_impl._response(
                "error", {"validated": False},
                diagnostics=[_diagnostic(
                    "memory_record_not_found", f"Memory record {memory_id!r} was not found.",
                    recovery_tools=["memory_search"], recovery_usage="memory_search()")],
                next_tools=["memory_search"], usage="")
        if not record.get("source_event"):
            return server_impl._response(
                "error", {"validated": False},
                diagnostics=[_diagnostic(
                    "memory_not_evidence_derived",
                    "Only evidence-derived records carrying Source event can use agent validation.",
                    recovery_tools=["memory_reconcile"], recovery_usage="")],
                next_tools=["memory_reconcile"], usage="")
        if record.get("validation") != "pending":
            return server_impl._response(
                "error", {"validated": False, "record": _memory_view(record, {})},
                diagnostics=[_diagnostic(
                    "memory_validation_not_pending",
                    "Agent validation requires an evidence-derived candidate with "
                    "Validation: pending. Finalized or malformed records are not rewritten "
                    "implicitly.",
                    recovery_tools=["memory_search"],
                    recovery_usage="memory_search(include_history=True)")],
                next_tools=["memory_search"], usage="")
        backfill_run = server_impl._load_script("memory_backfill").paused_run_for_source(
            root, str(record.get("source_event") or "")
        )
        missing_targets = [
            target for target in record.get("target_refs") or []
            if not _memory_file_target_exists(root, target)
        ]
        if verdict in ("promote", "retain", "rewrite") and missing_targets:
            return server_impl._response(
                "error", {"validated": False, "missing_targets": missing_targets},
                diagnostics=[_diagnostic(
                    "memory_target_not_current",
                    "One or more file targets are not present in the current tree.",
                    recovery_tools=["memory_validate"], recovery_usage="")],
                next_tools=["memory_validate"], usage="")

        rewritten: Optional[dict[str, Any]] = None
        if verdict == "rewrite":
            # A previous attempt may have created the replacement and then
            # failed while superseding the source. Reuse that exact corrected
            # record so retry converges instead of creating suffixed duplicates.
            existing_rewrite = next((
                candidate for candidate in records.values()
                if candidate["memory_id"] != memory_id
                and candidate.get("source_event") == record["source_event"]
                and candidate.get("validation") == "promote"
                and candidate.get("status") == "active"
                and candidate.get("kind") == rewrite_kind
                and candidate.get("summary") == str(rewrite_summary).strip()
                and sorted(candidate.get("evidence_refs") or [])
                == sorted(rewrite_evidence)
                and sorted(candidate.get("target_refs") or [])
                == sorted(rewrite_targets)
                and (not rewrite_title or candidate.get("title") == rewrite_title)
            ), None)
            if existing_rewrite is not None:
                rewritten = _memory_view(existing_rewrite, {})
            else:
                # Wave 1tdl8: the rewrite record inherits the rewritten
                # candidate's measured grounding cost (the rewrite path applies
                # supersession to the OLD record afterwards, so the inherited
                # cost is passed explicitly here rather than via `supersedes`).
                _prior_cost = record.get("source_exploration_cost")
                add = _memory_add_response_locked(
                    root, rewrite_kind, rewrite_summary, rewrite_evidence, rewrite_targets,
                    title=rewrite_title, confidence=rewrite_confidence, status="active",
                    abort_if_duplicate=False, _lock_held=True,
                    _source_event=record["source_event"], _validation="promote",
                    _validated_by="agent", _action_delta=str(action_delta).strip(),
                    _validation_rationale=str(rationale).strip(),
                    _evidence_verified=True, _current_target_verified=True,
                    _canonical_overlap=canonical_overlap,
                    _defer_index_refresh=bool(backfill_run),
                    _source_exploration_cost=(
                        int(_prior_cost)
                        if _prior_cost is not None and int(_prior_cost) > 0
                        else None
                    ),
                )
                if add.get("status") != "ok" or not add.get("data", {}).get("written"):
                    return server_impl._response(
                        "error", {"validated": False, "rewrite": add},
                        diagnostics=[_diagnostic(
                            "memory_rewrite_create_failed",
                            "The corrected record was not created; the source candidate is unchanged.",
                            recovery_tools=["memory_validate"], recovery_usage="")],
                        next_tools=["memory_validate"], usage="")
                rewritten = add["data"]["record"]
            replacement_id = rewritten["memory_id"]
        else:
            replacement_id = ""

        fence = _memory_fence(root)
        if fence is None:
            return server_impl._response(
                "error", {"validated": False, "rewrite_record": rewritten},
                diagnostics=[_diagnostic(
                    "memory_state_unwritable",
                    "Cannot establish the memory-state fence; validation was not recorded."
                    + (" The corrected record exists and must be reconciled manually."
                       if rewritten else ""),
                    recovery_tools=["memory_reconcile", "memory_validate"],
                    recovery_usage="")],
                next_tools=["memory_search"], usage="")
        try:
            path = mem.record_memory_validation(
                root, memory_id, verdict=verdict,
                action_delta=str(action_delta).strip(),
                rationale=str(rationale).strip(),
                evidence_verified=bool(evidence_verified),
                current_target_verified=bool(current_target_verified),
                canonical_overlap=canonical_overlap,
                superseded_by=replacement_id,
            )
        except (OSError, ValueError, FileNotFoundError) as exc:
            return server_impl._response(
                "error", {"validated": False, "rewrite_record": rewritten},
                diagnostics=[_diagnostic(
                    "memory_validation_write_failed",
                    f"Validation could not be recorded: {exc}."
                    + (" The corrected record exists; retry the same validation to "
                       "reuse it, or supersede the source manually."
                       if rewritten else ""),
                    recovery_tools=["memory_reconcile", "memory_validate"],
                    recovery_usage="")],
                next_tools=["memory_search"], usage="")
        finally:
            _memory_finalize(root, fence)
        changed = [path]
        if rewritten and rewritten.get("path"):
            changed.append(root / rewritten["path"])
        if not backfill_run:
            server_impl._trigger_background_index_refresh_for_paths(root, changed)
        updated = mem.parse_memory_record(path)
        return server_impl._response(
            "ok",
            {"validated": True, "verdict": verdict,
             "record": _memory_view(updated, {}) if updated else {"memory_id": memory_id},
             "rewrite_record": rewritten},
            diagnostics=[],
            next_tools=["memory_search", "memory_brief"],
            usage="memory_search(include_history=True)")


def _memory_query_records(
    root: Path, records: list[dict[str, Any]], query: str, index: Optional[server_impl.WaveIndex],
) -> tuple[Optional[list[dict[str, Any]]], dict[str, Any]]:
    """Return screened RRF candidates, or None for explicit lexical recovery.

    The calling agent still decides relevance and applicability. A model logit
    is not proof that a memory answers the question or establishes authority.
    """
    import server_impl
    retrieval = {
        "method": "lexical_policy", "qualification": "unavailable",
        "checked_candidate_cap": MEMORY_QUERY_CHECK_CAP, "checked_candidates": 0,
        "support_verified": False, "fallback_reason": "semantic_index_unavailable",
    }
    if index is None:
        return None, retrieval
    try:
        index._ensure_loaded()
        if index._docs_vector_layer is None:
            return None, retrieval
        retrieval["fallback_reason"] = "memory_candidate_state_unavailable"
        ranking = server_impl._load_script("memory_eval")
        by_id = {r["memory_id"]: r for r in records}
        if len(by_id) != len(records):
            return None, retrieval
        body_paths = {}
        expected_hashes = {}
        canonical_root = root.resolve()
        for record in records:
            if record.get("record_type") == "archive_register_entry":
                continue  # compact entries share a manifest; their identity is lexical
            source_path = Path(record["path"])
            if not source_path.is_absolute():
                source_path = canonical_root / source_path
            path = source_path.resolve().relative_to(canonical_root).as_posix()
            if path in body_paths:
                return None, retrieval
            body_paths[path] = record["memory_id"]
            retrieval["fallback_reason"] = "memory_source_state_stale"
            expected_hashes[path] = hashlib.sha256(source_path.read_bytes()).hexdigest()
        retrieval["fallback_reason"] = "memory_candidate_state_unavailable"
        dense = index._memory_candidate_scores(
            query, list(body_paths), expected_hashes=expected_hashes,
        )
        if dense.get("source_current") is False:
            retrieval["fallback_reason"] = "memory_source_state_stale"
            return None, retrieval
        if not dense["complete"]:
            # Includes intentionally unindexed historical bodies. Do not force
            # archive embedding or pass an incomplete dense stream as complete.
            retrieval["fallback_reason"] = "memory_vector_coverage_incomplete"
            return None, retrieval
        scores = dense["scores"]
        if any(not math.isfinite(float(value)) for value in scores.values()):
            return None, retrieval
        semantic = [body_paths[path] for path in sorted(scores, key=lambda p: (-scores[p], body_paths[p]))]
        lexical = ranking.lexical_bm25_order(records, query)[:MEMORY_SEARCH_CAP]
        order = ranking.reciprocal_rank_fusion([semantic, lexical])[:MEMORY_QUERY_CHECK_CAP]
        retrieval["semantic_assist"] = bool(semantic)
        if order:
            retrieval["fallback_reason"] = "memory_relevance_model_unavailable"
            reranker = index._get_memory_reranker()
            if reranker is None:
                return None, retrieval
            texts = [str(by_id[mid].get("summary") or by_id[mid].get("title") or "") for mid in order]
            raw = list(reranker.rerank(query, texts))
            if len(raw) != len(order) or any(isinstance(value, (bool, str, bytes)) for value in raw):
                return None, retrieval
            values = [float(value) for value in raw]
            if not all(math.isfinite(value) for value in values):
                return None, retrieval
            retrieval["checked_candidates"] = len(order)
            selected = [mid for mid, score in zip(order, values) if score >= MEMORY_QUERY_MIN_LOGIT]
        else:
            selected = []
        retrieval.update(method="hybrid_rrf", qualification="model_relevance",
                         fallback_reason=None)
        return [by_id[mid] for mid in selected], retrieval
    except Exception:
        # Never put query/model exception text into the response. Recovery is
        # the old eligible all-token lexical path, not unchecked dense hits.
        return None, retrieval


def memory_search_response(
    root: Path,
    query: str = "",
    target: str = "",
    symbol: str = "",
    kind: str = "",
    status: str = "",
    include_history: bool = False,
    limit: int = 10,
    index: Optional[server_impl.WaveIndex] = None,
) -> dict[str, Any]:
    import server_impl
    mem = _memory_mod()
    n = max(1, min(int(limit), MEMORY_SEARCH_CAP))
    if kind and kind not in mem.MEMORY_KINDS:
        return server_impl._response(
            "error", {"records": [], "count": 0},
            diagnostics=[_diagnostic("invalid_arguments",
                                     f"unknown kind {kind!r}; allowed: {', '.join(mem.MEMORY_KINDS)}",
                                     recovery_tools=["memory_search"], recovery_usage="memory_search()")],
            next_tools=["memory_search"], usage="",
        )
    statuses = (
        [status]
        if status
        else (None if include_history else list(mem.DEFAULT_SURFACED_STATUSES))
    )
    records = mem.load_memory_records(root, statuses=statuses)
    register_records: list[dict[str, Any]] = []
    if not include_history and not status and (query or target or symbol):
        register_records = mem.load_archive_register_entries(root)
        records.extend(register_records)
    if kind:
        records = [r for r in records if r["kind"] == kind]
    if target or symbol:
        records = [r for r in records if mem.match_targets(r, path=target, symbol=symbol)]
    retrieval = {"method": "policy", "qualification": "not_requested",
                 "checked_candidate_cap": MEMORY_QUERY_CHECK_CAP, "checked_candidates": 0,
                 "support_verified": False, "fallback_reason": None}
    query_order: Optional[dict[str, int]] = None
    if query:
        n = min(n, MEMORY_QUERY_CHECK_CAP)
        selected, retrieval = _memory_query_records(root, records, query, index)
        if selected is not None:
            records = selected
            query_order = {r["memory_id"]: i for i, r in enumerate(records)}
        else:
            # Existing all-token containment and authority ordering remain the
            # explicit recovery path when semantic/relevance infrastructure fails.
            tokens = [t for t in re.split(r"[^a-z0-9_]+", query.lower()) if t]
            def _text_match(r: dict[str, Any]) -> bool:
                haystack = " ".join([
                    (r.get("summary") or ""), (r.get("title") or ""),
                    " ".join(r.get("target_refs") or []),
                    " ".join(r.get("evidence_refs") or []),
                    " ".join(r.get("keywords") or []),
                ]).lower()
                return bool(tokens) and all(t in haystack for t in tokens)
            records = [r for r in records if _text_match(r)]
    ranked = _memory_ranked(root, records)
    if query_order is not None:
        # Preserve selected RRF order while retaining existing decay/provenance
        # metadata. Relevance ordering does not establish instruction authority.
        ranked.sort(key=lambda pair: query_order[pair[0]["memory_id"]])
    views = [_memory_view(record, decay) for record, decay in ranked[:n]]
    diagnostics = []
    if retrieval["qualification"] == "unavailable":
        model_unavailable = retrieval["fallback_reason"] == "memory_relevance_model_unavailable"
        recovery = (
            "Check the reranker disable setting and local model/runtime availability; "
            "run wf setup if provisioning is needed. After correcting availability, "
            "restart the MCP server to clear any cached model-load failure; "
            "an index refresh alone does not clear that cache."
            if model_unavailable else "Run index_health() and follow its index recovery guidance."
        )
        diagnostics.append(_diagnostic(
            "memory_query_fallback", "Memory relevance screening is unavailable; "
            "results use all-token lexical matching and policy ordering. "
            "The calling agent must assess each record's relevance and support. " + recovery,
            recovery_tools=[] if model_unavailable else ["index_health"],
            recovery_usage=recovery if model_unavailable else "index_health()",
        ))
    if not views:
        diagnostics.append(_diagnostic(
            "no_memory_matches",
            "No memory records matched. Memory is evidence-backed and sparse by design — "
            "absence of a record is not absence of risk.",
            recovery_tools=["memory_add"],
            recovery_usage="memory_add(kind=..., summary=..., evidence=[...], targets=[...])",
        ))
    return server_impl._response(
        "ok",
        {"records": views, "count": len(views),
         "statuses_searched": statuses or list(mem.MEMORY_STATUSES),
         "archive_register_entry_count": sum(
             1 for record in records
             if record.get("record_type") == "archive_register_entry"
         ),
         "archived_body_count": sum(
             1 for record in records
             if record.get("record_type") == "archive_body"
         ),
         "semantic_assist": bool(query_order is not None and retrieval.get("semantic_assist")),
         "retrieval": retrieval},
        diagnostics=diagnostics,
        next_tools=["memory_brief", "memory_reconcile"],
        usage="memory_brief(context='pre_implementation')",
    )


def memory_brief_response(
    root: Path,
    context: str = "pre_implementation",
    targets: Optional[list] = None,
    limit: int = MEMORY_BRIEF_CAP,
) -> dict[str, Any]:
    import server_impl
    mem = _memory_mod()
    context = (context or "pre_implementation").strip()
    if context not in MEMORY_BRIEF_CONTEXTS:
        return server_impl._response(
            "error", {"advisories": [], "count": 0},
            diagnostics=[_diagnostic("invalid_arguments",
                                     f"unknown context {context!r}; allowed: {', '.join(MEMORY_BRIEF_CONTEXTS)}",
                                     recovery_tools=["memory_brief"], recovery_usage="memory_brief()")],
            next_tools=["memory_brief"], usage="",
        )
    n = max(1, min(int(limit), MEMORY_BRIEF_CAP))
    target_list = [str(t).strip() for t in (targets or []) if str(t).strip()]
    records = mem.load_memory_records(root, statuses=mem.DEFAULT_SURFACED_STATUSES)
    ranked = _memory_ranked(root, records)
    ranked = [(r, d) for r, d in ranked if d.get("briefing_included", True)]
    if target_list:
        matched = [(r, d) for r, d in ranked
                   if any(mem.match_targets(r, path=t) for t in target_list)]
        unmatched = [(r, d) for r, d in ranked if (r, d) not in matched]
        ranked = matched + unmatched
    advisories = []
    community_scoped = []
    for record, decay in ranked[:n]:
        view = _memory_view(record, decay)
        if any(ref.startswith("community:") for ref in record.get("target_refs") or []):
            community_scoped.append(view)
        else:
            advisories.append(view)
    active_records = [record for record in records if record.get("status") == "active"]
    fragile_by_target: dict[str, list[str]] = {}
    for record in active_records:
        if record.get("kind") != "fragile_file":
            continue
        for target in record.get("target_refs") or []:
            target_s = mem._canonical_ref(str(target))
            if target_s:
                fragile_by_target.setdefault(target_s, []).append(str(record.get("memory_id") or ""))
    consolidation_candidates = [
        {"target": target, "memory_ids": ids}
        for target, ids in sorted(fragile_by_target.items())
        if len(ids) > 1
    ]
    active_count = len(active_records)
    data = {
        "context": context,
        "advisories": advisories,
        "count": len(advisories) + len(community_scoped),
        "cap": n,
        "total_surfaceable": len(ranked),
        "active_memory_budget": {
            "cap": mem.ACTIVE_MEMORY_CAP,
            "active_count": active_count,
            "remaining": max(0, mem.ACTIVE_MEMORY_CAP - active_count),
        },
    }
    if active_count >= mem.ACTIVE_MEMORY_CAP:
        data["curation_required"] = True
        data["consolidation_candidates"] = consolidation_candidates
    if community_scoped:
        data["community_scoped"] = community_scoped
    # 1svuk (telemetry-only, fail-isolated): accrue the SEPARATE estimated
    # exploration-avoided metric for the advisories actually surfaced here. This
    # never alters `data`/`advisories` (AC-6 invariance) and never touches the
    # measured Context Efficiency total.
    try:
        _credit_exploration_avoided_surface(root, ranked[:n], target_list, mem)
    except Exception:
        pass
    return server_impl._response(
        "ok", data,
        diagnostics=[],
        next_tools=["memory_search", "memory_reconcile"],
        usage="memory_search(query=...)",
    )


def memory_reconcile_response(
    root: Path,
    memory_id: str,
    status: str,
    superseded_by: str = "",
    archive_reason: str = "",
    eligibility_confirmed: bool = False,
    retain_for_history: bool = False,
) -> dict[str, Any]:
    """Serialize status/archive reconciliation across server processes."""
    import server_impl
    with server_impl.project_state_publication_lock(root):
        return _memory_reconcile_response_locked(
            root,
            memory_id,
            status,
            superseded_by=superseded_by,
            archive_reason=archive_reason,
            eligibility_confirmed=eligibility_confirmed,
            retain_for_history=retain_for_history,
        )


def _memory_reconcile_response_locked(
    root: Path,
    memory_id: str,
    status: str,
    superseded_by: str = "",
    archive_reason: str = "",
    eligibility_confirmed: bool = False,
    retain_for_history: bool = False,
) -> dict[str, Any]:
    import server_impl
    mem = _memory_mod()
    # Fence BEFORE the status rewrite (delivery-review round 4): refuse if the
    # durable fence cannot be established. Token is writer-owned.
    _fence_token = _memory_fence(root)
    if _fence_token is None:
        return server_impl._response(
            "error", {"updated": False},
            diagnostics=[_diagnostic(
                "memory_state_unwritable",
                "Cannot establish the memory-state fence (memory-state.sqlite is "
                "unwritable). Refusing the reconcile so no process serves a stale advisory.",
                recovery_tools=["memory_reconcile"], recovery_usage="")],
            next_tools=["memory_search"], usage="",
        )
    try:
        try:
            normalized_status = (status or "").strip()
            if normalized_status == "archived":
                if not retain_for_history:
                    return server_impl._response("error", {"updated": False}, diagnostics=[_diagnostic(
                        "memory_retention_decision_required",
                        "Archival retains history. Set retain_for_history=true only after confirming this retired record remains historically important; otherwise use memory_purge.",
                        recovery_tools=["memory_purge"], recovery_usage="memory_purge(memory_id=..., reviewed=true)")],
                        next_tools=["memory_purge"], usage="")
                archived = mem.archive_memory_record(
                    root,
                    (memory_id or "").strip(),
                    reason=(archive_reason or "").strip(),
                    eligibility_confirmed=bool(eligibility_confirmed),
                )
                path = archived["archive_path"]
            else:
                archived = None
                path = mem.reconcile_memory_record(
                    root, (memory_id or "").strip(), normalized_status,
                    superseded_by=(superseded_by or "").strip(),
                )
        except (FileNotFoundError, ValueError) as exc:
            return server_impl._response(
                "error", {"updated": False},
                diagnostics=[_diagnostic("memory_reconcile_failed", str(exc),
                                         recovery_tools=["memory_search"],
                                         recovery_usage="memory_search(include_history=True)")],
                next_tools=["memory_search"], usage="",
            )
    finally:
        _memory_finalize(root, _fence_token)
    changed_paths = [path]
    if archived:
        changed_paths.extend([
            root / mem.MEMORY_DIR / f"{(memory_id or '').strip()}.md",
            archived["register_path"],
        ])
    server_impl._trigger_background_index_refresh_for_paths(root, changed_paths)
    record = mem.parse_memory_record(path)
    decay = mem.apply_decay(record, index_dir=root / ".wavefoundry" / "index") if record else {}
    data = {
        "updated": True,
        "record": _memory_view(record, decay) if record else {"memory_id": memory_id},
    }
    if archived:
        data.update({
            "archived": True,
            "moved": archived["moved"],
            "no_op": archived["no_op"],
            "register_entry": _memory_view(archived["register_entry"], {}),
        })
    return server_impl._response(
        "ok",
        data,
        diagnostics=[],
        next_tools=["memory_search"],
        usage="memory_search(include_history=True)",
    )


def memory_purge_response(root: Path, memory_id: str, reviewed: bool = False,
                          eligibility_confirmed: bool = False) -> dict[str, Any]:
    """Permanently purge one reviewed, non-historic retired memory record."""
    import server_impl
    if not reviewed:
        return server_impl._response("error", {"purged": False}, diagnostics=[_diagnostic(
            "memory_purge_requires_review", "Purge is irreversible. Review the record and call again with reviewed=true.",
            recovery_tools=["memory_search"], recovery_usage="memory_search(include_history=True)")],
            next_tools=["memory_search"], usage="")
    mem = _memory_mod()
    with server_impl.project_state_publication_lock(root):
        fence = _memory_fence(root)
        if fence is None:
            return server_impl._response("error", {"purged": False}, diagnostics=[_diagnostic(
                "memory_state_unwritable", "Cannot establish the memory-state fence.")],
                next_tools=["memory_purge"], usage="")
        try:
            # Preserve source-event finality before removing its only corpus
            # record. The compact hash-only disposition lives in one
            # repo-visible file outside the indexed memory corpus, so it
            # survives index rebuilds and fresh clones. Refuse purge if that
            # write cannot be made: deletion must never make finalized history
            # eligible for proposal again.
            validated_id = mem.validate_memory_id(memory_id)
            _source_path, source = mem.resolve_purge_memory_source(
                root,
                validated_id,
                eligibility_confirmed=eligibility_confirmed,
            )
            if source is not None:
                source_event = str(source.get("source_event") or "").strip()
                if source_event:
                    disposition_path = mem.record_purged_source_event(root, source_event)
            result = mem.purge_memory_record(root, memory_id, eligibility_confirmed=eligibility_confirmed)
        except (FileNotFoundError, ValueError, OSError) as exc:
            return server_impl._response("error", {"purged": False}, diagnostics=[_diagnostic(
                "memory_purge_failed", str(exc),
                recovery_tools=["memory_purge", "memory_search"],
                recovery_usage=(
                    f"memory_purge(memory_id={memory_id!r}, reviewed=True)  # retry "
                    "the state-derived purge; inspect with memory_search(include_history=True)"
                ))], next_tools=["memory_purge", "memory_search"], usage="")
        finally:
            _memory_finalize(root, fence)
    server_impl._trigger_background_index_refresh_for_paths(root, [root / mem.MEMORY_ARCHIVE_MANIFEST])
    purge_data = {**result, "irreversible": True}
    if source is not None and source.get("source_event"):
        purge_data["disposition_path"] = str(disposition_path.relative_to(root).as_posix())
    return server_impl._response("ok", purge_data, diagnostics=[],
        next_tools=["memory_search"], usage="memory_search(include_history=True)")


def memory_consolidate_response(
    root: Path,
    mode: str = "dry_run",
    memory_ids: Optional[list[str]] = None,
    title: str = "",
    summary: str = "",
    reviewed: bool = False,
    eligibility_confirmed: bool = False,
    limit: int = 10,
) -> dict[str, Any]:
    """Preview or apply one small, explicitly reviewed memory consolidation."""
    import server_impl
    mem = _memory_mod()
    mode = str(mode or "dry_run").strip().lower()
    if mode not in {"dry_run", "create"}:
        return server_impl._response("error", {"mode": mode}, diagnostics=[_diagnostic(
            "invalid_arguments", "mode must be dry_run or create")],
            next_tools=["memory_consolidate"], usage="")
    try:
        group_limit = max(1, min(int(limit), MEMORY_CONSOLIDATE_GROUP_CAP))
    except (TypeError, ValueError):
        group_limit = MEMORY_CONSOLIDATE_GROUP_CAP
    records = mem.load_memory_records(root, statuses=("active", "candidate"))
    groups: dict[tuple[str, tuple[str, ...]], list[dict[str, Any]]] = {}
    for record in records:
        targets = tuple(sorted(set(record.get("target_refs") or [])))
        if targets:
            groups.setdefault((str(record.get("kind") or ""), targets), []).append(record)
    proposals: list[dict[str, Any]] = []
    skipped_groups: list[dict[str, Any]] = []
    for (kind, targets), members in sorted(groups.items()):
        members.sort(key=lambda item: item["memory_id"])
        if len(members) < 2:
            if len(skipped_groups) < group_limit:
                skipped_groups.append({
                    "kind": kind,
                    "targets": list(targets),
                    "memory_ids": [item["memory_id"] for item in members],
                    "reason": "fewer_than_two_related_records",
                })
            continue
        selected_members = members[:MEMORY_CONSOLIDATE_MEMBER_CAP]
        source_views = []
        for item in selected_members:
            source_summary = str(item.get("summary") or "")
            source_views.append({
                "memory_id": item["memory_id"],
                "title": item.get("title"),
                "kind": item.get("kind"),
                "status": item.get("status"),
                "summary": source_summary[:MEMORY_SUMMARY_EXCERPT_CHARS],
                "summary_truncated": len(source_summary) > MEMORY_SUMMARY_EXCERPT_CHARS,
                "evidence_refs": list(item.get("evidence_refs") or []),
                "target_refs": list(item.get("target_refs") or []),
            })
        proposed_summary = " ".join(
            str(item.get("summary") or "").strip() for item in selected_members
        ).strip()[:MEMORY_SUMMARY_EXCERPT_CHARS]
        proposals.append({
            "memory_ids": [item["memory_id"] for item in selected_members],
            "kind": kind, "targets": list(targets),
            "sources": source_views,
            "proposed_title": f"Consolidated {kind.replace('_', ' ')} playbook",
            "proposed_summary": proposed_summary,
            "total_members": len(members),
            "remaining_count": max(0, len(members) - len(selected_members)),
            "truncated": len(members) > len(selected_members),
            "requires_reviewed_apply": True,
        })
    groups_total = len(proposals)
    proposals = proposals[:group_limit]
    preview_data = {
        "mode": mode,
        "groups": proposals,
        "groups_total": groups_total,
        "groups_returned": len(proposals),
        "groups_omitted": max(0, groups_total - len(proposals)),
        "member_cap": MEMORY_CONSOLIDATE_MEMBER_CAP,
        "skipped_groups": skipped_groups,
        "skipped": "Only same-kind records with identical canonical targets are grouped.",
    }
    if mode == "dry_run":
        return server_impl._response("dry_run", preview_data,
            diagnostics=[], next_tools=["memory_consolidate"],
            usage="memory_consolidate(mode='create', memory_ids=[...], title=..., summary=..., reviewed=True)")
    selected = [str(item or "").strip() for item in (memory_ids or [])]
    match = next((item for item in proposals if item["memory_ids"] == sorted(selected)), None)
    if match is None or not reviewed or not title.strip() or not summary.strip():
        return server_impl._response("error", preview_data, diagnostics=[_diagnostic(
            "memory_consolidation_requires_review", "Select one previewed group and supply title, summary, and reviewed=true.",
            recovery_tools=["memory_consolidate"], recovery_usage="memory_consolidate(mode='dry_run')")],
            next_tools=["memory_consolidate"], usage="memory_consolidate(mode='dry_run')")
    source_snapshots: dict[str, bytes] = {}
    manifest_path = root / mem.MEMORY_ARCHIVE_MANIFEST
    manifest_before: Optional[bytes] = None
    replacement_path: Optional[Path] = None
    replacement_id = ""
    archived: list[dict[str, Any]] = []
    rollback_completed = False
    with server_impl.project_state_publication_lock(root):
        fence = _memory_fence(root)
        if fence is None:
            return server_impl._response("error", {"updated": False}, diagnostics=[_diagnostic(
                "memory_state_unwritable", "Cannot establish the memory-state fence." )],
                next_tools=["memory_consolidate"], usage="")
        try:
            # Re-check the previewed group under the mutation lock before the
            # replacement or any source status changes. In particular, a
            # protected-kind refusal must be byte-pure instead of leaving a
            # replacement plus a partially superseded group.
            for memory_id in match["memory_ids"]:
                source_path = root / mem.MEMORY_DIR / f"{memory_id}.md"
                source = mem.parse_memory_record(source_path)
                if source is None:
                    raise ValueError(f"{memory_id}: memory record is missing or malformed")
                if source.get("status") not in {"active", "candidate"}:
                    raise ValueError(f"{memory_id}: source status changed; preview again")
                if str(source.get("kind") or "") != match["kind"] or sorted(
                    set(source.get("target_refs") or [])
                ) != match["targets"]:
                    raise ValueError(f"{memory_id}: consolidation group changed; preview again")
                archive_path = root / mem.MEMORY_ARCHIVE_DIR / f"{memory_id}.md"
                if archive_path.exists():
                    raise ValueError(f"{memory_id}: archive body already exists")
                if source.get("kind") in mem.ARCHIVE_PROTECTED_KINDS and not eligibility_confirmed:
                    raise ValueError(
                        f"{memory_id}: {source['kind']} is protected; set "
                        "eligibility_confirmed=true only after current review"
                    )
                source_snapshots[memory_id] = source_path.read_bytes()
            manifest_before = manifest_path.read_bytes() if manifest_path.is_file() else None
            evidence = [f"consolidated from {item}" for item in match["memory_ids"]]
            added = _memory_add_response_locked(
                root,
                match["kind"],
                summary.strip(),
                evidence,
                match["targets"],
                title=title.strip(),
                status="active",
                supersedes=match["memory_ids"][0],
                _lock_held=True,
                _defer_index_refresh=True,
            )
            if added.get("status") != "ok":
                return server_impl._response(
                    "error",
                    {"updated": False},
                    diagnostics=list(added.get("diagnostics") or []),
                    next_tools=["memory_consolidate"],
                    usage="memory_consolidate(mode='dry_run')",
                )
            replacement_id = str(added["data"]["record"]["memory_id"])
            replacement_path = root / mem.MEMORY_DIR / f"{replacement_id}.md"
            for memory_id in match["memory_ids"]:
                mem.reconcile_memory_record(root, memory_id, "superseded", superseded_by=replacement_id)
                archived.append(mem.archive_memory_record(root, memory_id,
                    reason=f"consolidated into {replacement_id}",
                    eligibility_confirmed=eligibility_confirmed))
        except (ValueError, FileNotFoundError, FileExistsError, OSError, RuntimeError) as exc:
            rollback_error = ""
            try:
                if replacement_path is not None and replacement_path.exists():
                    replacement_path.unlink()
                for source_id, content in source_snapshots.items():
                    archive_path = root / mem.MEMORY_ARCHIVE_DIR / f"{source_id}.md"
                    if archive_path.exists():
                        archive_path.unlink()
                    active_path = root / mem.MEMORY_DIR / f"{source_id}.md"
                    active_path.parent.mkdir(parents=True, exist_ok=True)
                    active_path.write_bytes(content)
                if manifest_before is None:
                    if manifest_path.exists():
                        manifest_path.unlink()
                else:
                    manifest_path.parent.mkdir(parents=True, exist_ok=True)
                    manifest_path.write_bytes(manifest_before)
                rollback_completed = True
            except OSError as rollback_exc:
                rollback_error = f"; rollback incomplete: {rollback_exc}"
            return server_impl._response("error", {
                "updated": False,
                "rollback_completed": rollback_completed,
                "replacement_id": replacement_id or None,
            }, diagnostics=[_diagnostic(
                "memory_consolidation_failed", f"{exc}{rollback_error}", recovery_tools=["memory_consolidate"], recovery_usage="memory_consolidate(mode='dry_run')")],
                next_tools=["memory_consolidate"], usage="")
        finally:
            _memory_finalize(root, fence)
    changed = [replacement_path, *(item["archive_path"] for item in archived), manifest_path]
    server_impl._trigger_background_index_refresh_for_paths(root, changed)
    return server_impl._response("ok", {"updated": True, "replacement_id": replacement_id,
        "archived_ids": match["memory_ids"]}, diagnostics=[], next_tools=["memory_search"],
        usage="memory_search(include_history=True)")


def wf_memory_eval_response(root: Path) -> dict[str, Any]:
    """Curated memory-retrieval measurement for the configured repository.

    Wave 1tgws: the curated pass is a cross-project capability, so it is
    reachable through the tool surface rather than only a checked-out script.
    It measures the CONFIGURED root — like every other tool, and per the
    allowed-roots safety rule, the caller does not name a target directory.
    Aggregate-only by construction: the engine's report carries metrics,
    kind/status counts, a fingerprint, and a non-qualification notice, never
    record bodies or ids. Self-summary probes cannot authorize adoption.
    """
    import server_impl
    target = root
    evaluator = server_impl._load_script("memory_eval")
    report = evaluator.run_curated(target)
    available = bool(report.get("available"))
    diagnostics: list[dict[str, Any]] = []
    if not available:
        diagnostics.append({
            "code": "curated_pass_unavailable",
            "message": (
                "the curated corpus pass could not run: "
                f"{report.get('unavailable_reason') or 'semantic backend or corpus unavailable'}. "
                "Build the index (index_build) and ensure the repository has "
                "memory records, then retry."
            ),
            "recovery_tools": ["index_build", "index_health", "memory_search"],
            "recovery_usage": "index_health()",
        })
    return {
        "status": "ok",
        "data": {"root": str(target), **report},
        "diagnostics": diagnostics,
        "next_tools": ["memory_search", "memory_brief"],
        "usage": "memory_search(query='...')",
    }

