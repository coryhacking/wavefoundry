#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import venv_bootstrap  # the single venv resolver (wave 1p7pl)

# Activate the shared tool venv IN-PROCESS before any heavy work (wave 1p7pl/1p802). No-op when
# already in the venv or when it does not exist yet (fresh bootstrap).
venv_bootstrap.activate_tool_venv()


BASE36_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"
# Residual v1-only fallback for repos with no lifecycle_id_policy block. NOT a
# provisioning source: v2 epochs are computed at provisioning time by
# `compute_provisioning_epoch` (compute-or-error, never this constant).
DEFAULT_EPOCH_UTC = datetime(2020, 2, 2, 2, 2, tzinfo=timezone.utc)
SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")

# ── v2 scheme constants ───────────────────────────────────────────────────────
#
# v2 value = offset + day_index * ENTROPY_SPACE + entropy, base36, min-width 5,
# NO modulo. `day_index` is whole days since the provisioning epoch; `entropy`
# is 12 deterministic bits of blake2s(kind + "\x00" + slug). The offset places
# every new ID above all pre-migration IDs (value order == time order across
# the v1→v2 cutover) and sets the fresh-install start band. Past 36^5 the value
# encodes naturally to 6 chars (a safety valve ~40 years out, never a wrap).
_ENTROPY_SPACE = 4096          # 12 bits — the power-of-2 knee within 5 base36 chars
_ENTROPY_DIGEST_SIZE = 8       # blake2s digest bytes; 2^64 % 4096 == 0 → uniform
_V2_VALUES_PER_DAY = _ENTROPY_SPACE

# Fresh-install offset band [36^3, 619,520): first char `0`, second char `1`-`d`,
# never `0000x`. 619,520 = 36^5 - 14,610*4096 - 4096 — the cap at which the
# worst-case (top-of-band, max day-0 entropy) horizon to the 6-char overflow is
# exactly 40.0 years (14,610 days).
FRESH_OFFSET_FLOOR = 36 ** 3   # 46,656
FRESH_OFFSET_CAP = 619_520

# Migrated-repo offset margin above the scanned pre-migration max. Sized to
# cover the intended maximum v1-sibling-branch merge window: v1 climbs ~288/day,
# so a branch still minting v1 for up to MARGIN/288 days (~1 year) before
# merging stays below the v2 band. Beyond that window the "new > all existing"
# invariant is an accepted, documented bound.
V1_MERGE_MARGIN = 288 * 366  # 105,408 ≈ 1 year of v1 drift

# Loud operator warning when fewer than ~2 years of 5-char space remain, so the
# 6-char widening is a deliberate, anticipated event rather than a surprise.
_NEAR_HORIZON_MARGIN = 730 * _V2_VALUES_PER_DAY  # ~2 years of daily values
_V2_FIVE_CHAR_CEILING = 36 ** 5

# In-process floor: tracks the last prefix assigned in this process so rapid
# same-second calls produce unique prefixes before the filesystem scan sees the
# earlier write.  Subprocess invocations always start with None (fresh module).
# The floor is scoped to the policy that minted it (`_last_assigned_policy`):
# raw decoded values are not comparable across schemes/offsets, so a mint under
# a different policy (e.g. a v1 mint followed by a fresh-band v2 mint in one
# process) must not inherit the other policy's floor (delivery red-team F4).
_last_assigned_prefix: str | None = None
_last_assigned_policy: tuple | None = None


def discover_repo_root() -> Path | None:
    """Walk up from CWD to find the repo root anchored by ``workflow-config.json``.

    Intentional differences from the copies in other scripts:
    - Returns ``None`` (instead of CWD) when no anchor is found — callers that
      need a guaranteed path should handle the ``None`` case.
    - Also tries the script's own grandparent directory as a last-resort anchor
      (useful when the script is invoked from inside the framework bundle).

    Cross-reference: ``server._discover_root``, ``indexer._discover_root``,
    ``render_platform_surfaces.discover_repo_root``, ``docs_gardener.project_root``.
    A future consolidation task should unify these into a shared utility.
    """
    for env_key in ("PROJECT_ROOT", "REPO_ROOT"):
        raw = os.environ.get(env_key)
        if raw:
            candidate = Path(raw).expanduser().resolve()
            if (candidate / "docs" / "workflow-config.json").is_file():
                return candidate
    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if (candidate / "docs" / "workflow-config.json").is_file():
            return candidate
    script = Path(__file__).resolve()
    anchor = script.parents[3]
    if (anchor / "docs" / "workflow-config.json").is_file():
        return anchor
    return None


def parse_epoch_utc(raw: str) -> datetime:
    text = raw.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def load_lifecycle_policy(repo_root: Path | None = None) -> tuple[datetime, int, int, str]:
    """Return ``(epoch_utc, hour_offset, offset, scheme_version)`` from docs/workflow-config.json.

    Silent v1 defaults apply ONLY when the policy block is genuinely absent
    (missing file/block, or unreadable file — the latter with a stderr warning).
    When ``scheme_version`` is present it is validated strictly and malformed
    values raise ``ValueError``: a silently-defaulted v2 offset would mint in or
    below the reserved band, and a silent v1 revert on a migrated repo would
    mis-order every new ID.

    ``hour_offset`` is v1-only (ignored by v2); ``offset`` is v2-only (ignored
    by v1). Both ride in one tuple so each scheme's path stays byte-unchanged.
    """
    root = repo_root or discover_repo_root()
    default: tuple[datetime, int, int, str] = (DEFAULT_EPOCH_UTC, 0, 0, "v1")
    if root is None:
        return default
    cfg = root / "docs" / "workflow-config.json"
    if not cfg.is_file():
        return default
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(
            f"lifecycle_id: warning: could not parse {cfg} ({exc}); "
            "falling back to v1 defaults for this mint",
            file=sys.stderr,
        )
        return default
    policy = data.get("lifecycle_id_policy")
    if policy is not None and not isinstance(policy, dict):
        # A present-but-wrong-type block on a migrated repo would silently
        # revert minting to v1 defaults (mis-ordered, below-band IDs) — warn
        # loudly; docs-lint flags the same condition as an error.
        print(
            "lifecycle_id: warning: lifecycle_id_policy in workflow-config.json is "
            f"not an object (got {type(policy).__name__}); falling back to v1 defaults "
            "for this mint",
            file=sys.stderr,
        )
        return default
    if policy is None:
        return default

    scheme_raw = policy.get("scheme_version")
    if scheme_raw is None:
        scheme = "v1"
    elif scheme_raw in ("v1", "v2"):
        scheme = scheme_raw
    else:
        raise ValueError(
            "workflow-config lifecycle_id_policy.scheme_version must be 'v1' or 'v2' "
            f"when set; got {scheme_raw!r}"
        )

    epoch: datetime
    epoch_raw = policy.get("epoch_utc")
    if isinstance(epoch_raw, str) and epoch_raw.strip():
        epoch = parse_epoch_utc(epoch_raw)
    elif scheme == "v2":
        raise ValueError(
            "workflow-config lifecycle_id_policy.epoch_utc is required and must be a "
            "valid UTC ISO-8601 string when scheme_version is 'v2'"
        )
    else:
        epoch = DEFAULT_EPOCH_UTC

    hour_offset = policy.get("hour_offset", 0)
    if isinstance(hour_offset, bool) or not isinstance(hour_offset, int):
        raise ValueError("workflow-config lifecycle_id_policy.hour_offset must be a non-negative integer")
    if hour_offset < 0:
        raise ValueError("workflow-config lifecycle_id_policy.hour_offset must be non-negative")

    offset = policy.get("offset", 0)
    if scheme == "v2":
        if isinstance(offset, bool) or not isinstance(offset, int):
            raise ValueError("workflow-config lifecycle_id_policy.offset must be an integer when scheme_version is 'v2'")
        if offset < FRESH_OFFSET_FLOOR:
            raise ValueError(
                "workflow-config lifecycle_id_policy.offset must be >= 36^3 "
                f"({FRESH_OFFSET_FLOOR}) when scheme_version is 'v2'; got {offset!r}"
            )
        node_bits = policy.get("node_bits", 0)
        if node_bits not in (0, None):
            raise ValueError(
                "workflow-config lifecycle_id_policy.node_bits is reserved and must be 0 "
                "(unset = full 12-bit hash entropy); explicit node assignment is not yet supported"
            )
    elif isinstance(offset, bool) or not isinstance(offset, int):
        offset = 0  # v1 ignores offset entirely; tolerate junk for byte-unchanged v1 behavior

    return epoch, hour_offset, offset, scheme


def encode_base36(value: int) -> str:
    if value < 0:
        raise ValueError("value must be non-negative")
    if value == 0:
        return "0"

    encoded: list[str] = []
    remaining = value
    while remaining > 0:
        remaining, digit = divmod(remaining, 36)
        encoded.append(BASE36_ALPHABET[digit])
    return "".join(reversed(encoded))


def decode_base36(s: str) -> int:
    return int(s, 36)


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


# v1 encoding — wave 131bt close-out (131bu): integer-packed 5-minute buckets.
#
# Prior scheme appended ``BASE36[elapsed_minutes % 36]`` as the tail char, which
# wraps every 36 minutes — breaking the "lex order = creation order" guarantee.
# v1 packs ``(days_since_epoch * 288 + bucket_5min) mod 36^5`` as a single
# base36 number, padded to 5 chars. Lex order matches wall-clock order across
# any day boundary within the 36^5 / 288 = 209,952 day (~575 year) horizon.
#
# 5-minute buckets (288 per day) align with whole-minute boundaries and whole-
# second boundaries (300 sec each); divide 36^5 cleanly with zero wasted slots
# (60,466,176 / 288 = 209,952 exact). v1 spends the whole 5-char budget on the
# time axis — zero collision resistance across branches, which is why v2
# reallocates the over-provisioned horizon into per-mint hash entropy. The
# build_pack.py suffix computes its own pure-time index and no longer derives
# from this prefix.
_BUCKETS_PER_DAY = 288
_BUCKET_WIDTH_MIN = 5
_PREFIX_MOD = 36 ** 5  # 60,466,176


def _packed_value(now_utc: datetime, epoch_utc: datetime, hour_offset_buckets: int = 0) -> int:
    days = (now_utc.date() - epoch_utc.date()).days
    if days < 0:
        raise ValueError(
            f"timestamp must not be earlier than the configured lifecycle epoch "
            f"({epoch_utc.isoformat().replace('+00:00', 'Z')}); got {now_utc.isoformat()}"
        )
    bucket = (now_utc.hour * 60 + now_utc.minute) // _BUCKET_WIDTH_MIN
    packed = days * _BUCKETS_PER_DAY + bucket + hour_offset_buckets
    return packed % _PREFIX_MOD


# ── v2 encoding ───────────────────────────────────────────────────────────────
#
# Frozen entropy contract (locked by a golden-vector test): blake2s, digest_size
# _ENTROPY_DIGEST_SIZE, big-endian int extraction, UTF-8 `kind + "\x00" + slug`
# input, `% 4096`. Changing ANY of these silently re-maps every future ID while
# `scheme_version` stays "v2" — do not touch without a new scheme version.
#
# Node-carve forward compatibility: when explicit node assignment ships, the top
# 4 bits become `(node_id << 8) | (hash % 256)` ONLY when `node_bits` is set in
# policy. Node unset (today, always) = full 12-bit hash — a hard 4/8 split from
# day one would silently narrow entropy 4096→256 and quadruple collision rates.

def _v2_entropy(kind: str, slug: str) -> int:
    data = f"{kind}\x00{slug}".encode("utf-8")
    digest = hashlib.blake2s(data, digest_size=_ENTROPY_DIGEST_SIZE).digest()
    return int.from_bytes(digest, "big") % _ENTROPY_SPACE


def _v2_value(now_utc: datetime, epoch_utc: datetime, offset: int, kind: str, slug: str) -> int:
    """v2 base value: ``offset + day_index * 4096 + entropy`` — NO modulo.

    Non-overlapping day bands keep value order == time order for any entropy;
    past 36^5 the value simply encodes to 6 base36 chars (never wraps).
    """
    day_index = (now_utc.date() - epoch_utc.date()).days
    if day_index < 0:
        raise ValueError(
            f"timestamp must not be earlier than the configured lifecycle epoch "
            f"({epoch_utc.isoformat().replace('+00:00', 'Z')}); got {now_utc.isoformat()}"
        )
    return offset + day_index * _V2_VALUES_PER_DAY + _v2_entropy(kind, slug)


def _warn_if_near_horizon(value: int) -> None:
    if _V2_FIVE_CHAR_CEILING - _NEAR_HORIZON_MARGIN <= value < _V2_FIVE_CHAR_CEILING:
        print(
            "lifecycle_id: WARNING: less than ~2 years of 5-character ID space remain "
            "before the graceful 6-character widening. Plan a deliberate re-issue "
            "(new epoch/offset provisioning) or accept 6-character IDs.",
            file=sys.stderr,
        )


def _normalize_policy(
    policy: tuple[datetime, int] | tuple[datetime, int, int, str],
) -> tuple[datetime, int, int, str]:
    """Accept the legacy 2-tuple ``(epoch, hour_offset)`` or the widened 4-tuple.

    Existing callers and tests pass 2-tuples; those are v1 by construction.
    """
    if len(policy) == 2:
        epoch, hour_offset = policy
        return epoch, hour_offset, 0, "v1"
    if len(policy) == 4:
        return policy  # type: ignore[return-value]
    raise ValueError(
        "policy must be (epoch_utc, hour_offset) or (epoch_utc, hour_offset, offset, scheme_version)"
    )


def build_prefix(
    timestamp: datetime | None = None,
    *,
    policy: tuple[datetime, int] | tuple[datetime, int, int, str] | None = None,
    kind: str = "",
    slug: str = "",
) -> str:
    """Return the base36 lifecycle prefix for ``timestamp`` (default: now UTC).

    Scheme is dispatched from the policy's ``scheme_version``:

    - ``v1`` (default / legacy 2-tuple policy): ``(days_since_epoch * 288 +
      bucket_5min) mod 36^5``, right-padded to 5 chars — byte-unchanged from the
      pre-v2 implementation. ``hour_offset`` is applied as ``hour_offset * 12``
      buckets; ``kind``/``slug`` are ignored.
    - ``v2``: ``offset + days_since_epoch * 4096 + blake2s-entropy(kind, slug)``,
      min-width 5, no modulo — values past 36^5 encode naturally to 6 chars.

    Value order matches wall-clock order under both schemes (and across the
    cutover, via the provisioned offset). Lex order holds within equal width;
    at the 6-char overflow, ordering consumers must sort by decoded value.
    """
    current_time = (timestamp or current_utc_time()).astimezone(timezone.utc)
    raw_policy = policy if policy is not None else load_lifecycle_policy()
    epoch, hour_offset, offset, scheme = _normalize_policy(raw_policy)
    if scheme == "v2":
        value = _v2_value(current_time, epoch, offset, kind, slug)
        _warn_if_near_horizon(value)
        return encode_base36(value).rjust(5, "0")
    hour_offset_buckets = hour_offset * (60 // _BUCKET_WIDTH_MIN)  # hour_offset hours → buckets
    packed = _packed_value(current_time, epoch, hour_offset_buckets)
    return encode_base36(packed).rjust(5, "0")


# Width 5-6: 5 is the standard width; 6 is the graceful post-horizon overflow
# (a 6-char value is always > every 5-char value, so dedup stays sound).
_PREFIX_RE = re.compile(r"^([0-9a-z]{5,6})[-\s]")


def _existing_prefixes(repo_root: Path) -> set[str]:
    prefixes: set[str] = set()
    plans_dir = repo_root / "docs" / "plans"
    if plans_dir.is_dir():
        for p in plans_dir.glob("*.md"):
            m = _PREFIX_RE.match(p.stem)
            if m:
                prefixes.add(m.group(1))
    waves_dir = repo_root / "docs" / "waves"
    if waves_dir.is_dir():
        for wave_dir in waves_dir.iterdir():
            if wave_dir.is_dir():
                m = _PREFIX_RE.match(wave_dir.name)
                if m:
                    prefixes.add(m.group(1))
        for p in waves_dir.glob("*/*.md"):
            m = _PREFIX_RE.match(p.stem)
            if m:
                prefixes.add(m.group(1))
    # Wave 1p45b — also dedup against ADR stems so a new mint never collides with
    # an existing architecture-decision record.
    adr_dir = repo_root / "docs" / "architecture" / "decisions"
    if adr_dir.is_dir():
        for p in adr_dir.glob("*.md"):
            m = _PREFIX_RE.match(p.stem)
            if m:
                prefixes.add(m.group(1))
    return prefixes


# ── v2 provisioning compute helpers ──────────────────────────────────────────
#
# Pure functions (no file writes) so provisioning is deterministic and
# unit-testable. File-write orchestration lives in
# ``upgrade_wavefoundry.materialize_lifecycle_policy`` — the seeds call that
# script; agents never hand-compute epochs or offsets.

def scan_max_prefix_value(repo_root: Path) -> int | None:
    """Return the max decoded value among existing non-legacy lifecycle prefixes.

    ``None`` means a fresh repo (no minted IDs — the reserved ``00000`` baseline
    does not count as history).

    Only 5-char prefixes count: v1 history is 5 chars by construction
    (``mod 36^5``), and a repo already carrying 6-char v2 IDs never reaches this
    scan (migration is keyed on ``scheme_version`` absence). A 6-char match here
    is therefore always a word-like false positive (delivery red-team: a stray
    ``review-notes.md`` would otherwise decode above 36^5 and silently freeze an
    offset that makes every future ID 6 chars from day one).
    """
    values = [
        decode_base36(p)
        for p in _existing_prefixes(repo_root)
        if p != "00000" and len(p) == 5
    ]
    return max(values) if values else None


def compute_migrated_offset(scanned_max: int) -> int:
    """Offset for a repo with v1 history: clears the scanned max by the margin.

    The "new > all existing" invariant is time-bounded by ``V1_MERGE_MARGIN``
    (a v1 sibling branch minting for more than MARGIN/288 days before merging
    exceeds the early v2 band — accepted, documented bound).
    """
    if scanned_max < 0:
        raise ValueError("scanned_max must be non-negative")
    return scanned_max + V1_MERGE_MARGIN


def compute_fresh_offset(project_seed: str) -> int:
    """Deterministic fresh-install offset scattered into ``[36^3, 619,520)``.

    First mint reads first char ``0``, second char ``1``-``d``, never ``0000x``;
    572,864 start points; worst-case horizon to the 6-char overflow exactly
    40.0 years. No RNG — the seed is captured once at provisioning and fixed
    in config.
    """
    if not project_seed:
        raise ValueError("project_seed must be a non-empty string")
    digest = hashlib.blake2s(project_seed.encode("utf-8"), digest_size=8).digest()
    span = FRESH_OFFSET_CAP - FRESH_OFFSET_FLOOR
    return FRESH_OFFSET_FLOOR + int.from_bytes(digest, "big") % span


def compute_provisioning_epoch(now_utc: datetime) -> str:
    """Provisioning-time epoch: midnight UTC of the install/rollout date.

    Compute-or-error — never a stale fixed year (``DEFAULT_EPOCH_UTC`` and any
    past-dated formula are retired from provisioning; day_index starts at ~0 so
    no horizon is burned).
    """
    if now_utc is None or now_utc.tzinfo is None:
        raise ValueError("now_utc must be a timezone-aware datetime")
    day = now_utc.astimezone(timezone.utc).date()
    return f"{day.isoformat()}T00:00:00Z"


def compute_v2_policy_fields(
    repo_root: Path,
    now_utc: datetime,
    project_label: str,
) -> dict:
    """Compute the v2 ``lifecycle_id_policy`` field values for ``repo_root``.

    Migrated repos (existing minted IDs) get ``offset = scanned_max + margin``
    (continuing the existing band); fresh repos get the deterministic scattered
    start band and record their ``project_seed``. Pure compute — the caller
    owns the read-modify-write of workflow-config.json.
    """
    epoch = compute_provisioning_epoch(now_utc)
    scanned_max = scan_max_prefix_value(repo_root)
    fields: dict = {
        "epoch_utc": epoch,
        "scheme_version": "v2",
        "node_bits": 0,
    }
    if scanned_max is None:
        seed = f"{now_utc.astimezone(timezone.utc).isoformat()}|{project_label}"
        fields["offset"] = compute_fresh_offset(seed)
        fields["project_seed"] = seed
    else:
        fields["offset"] = compute_migrated_offset(scanned_max)
    return fields


# Wave 1p45b — sentinel distinguishing "repo_root not supplied" (→ fall back to
# discover_repo_root() and dedup by default) from an EXPLICIT None (→ no on-disk
# scan, the pre-existing opt-out behavior tests rely on).
_UNSET = object()


def next_available_prefix(
    timestamp: datetime | None = None,
    *,
    policy: tuple[datetime, int] | tuple[datetime, int, int, str] | None = None,
    repo_root: Path | None = _UNSET,  # type: ignore[assignment]
    commit: bool = True,
    kind: str = "",
    slug: str = "",
) -> str:
    """Return the next available lifecycle prefix.

    When ``commit=True`` (default), mutates the module-level
    ``_last_assigned_prefix`` so subsequent calls advance past this prefix.
    When ``commit=False`` (peek mode, wave 1p3dk / 1p3ds), returns the same
    prefix without mutation — a subsequent ``commit=True`` call returns the
    same prefix and only then advances. Used for ``dry_run`` MCP tool paths
    so previewing a wave or change doesn't burn the lifecycle slot.

    ``kind``/``slug`` feed the v2 entropy hash (ignored under v1). The linear
    probe below is the same-repo tiebreaker on top of the base value, so a v2
    ID equals its deterministic base absent a local same-day probe collision.
    """
    global _last_assigned_prefix, _last_assigned_policy
    # Policy/dedup coherence: when the caller names a repo_root, the POLICY is
    # loaded from that same repo — not from ambient CWD/env discovery. A mint
    # scoped to repo X must encode under X's scheme/epoch/offset (the secrets
    # scanner and MCP tools pass explicit roots; discovery is only the fallback).
    effective_policy = _normalize_policy(
        policy if policy is not None else load_lifecycle_policy(
            repo_root if repo_root is not _UNSET else None
        )
    )
    base = build_prefix(timestamp, policy=effective_policy, kind=kind, slug=slug)
    # Wave 1p45b — when repo_root is not supplied, dedup against the discovered
    # repo by default; an EXPLICIT None opts out of the on-disk scan (empty set).
    if repo_root is _UNSET:
        repo_root = discover_repo_root()
    existing = _existing_prefixes(repo_root) if repo_root is not None else set()

    # Start from the greater of the time-based prefix and one past the last
    # in-process assignment.  This prevents rapid same-second calls from
    # returning identical prefixes before the earlier directory write is visible
    # to the filesystem scan. The floor applies ONLY under the policy that set
    # it — decoded values are not comparable across schemes/offsets.
    start_n = decode_base36(base)
    if _last_assigned_prefix is not None and _last_assigned_policy == effective_policy:
        last_n = decode_base36(_last_assigned_prefix)
        if last_n >= start_n:
            start_n = last_n + 1

    n = start_n
    while True:
        candidate = encode_base36(n).rjust(5, "0")
        if candidate not in existing:
            if commit:
                _last_assigned_prefix = candidate
                _last_assigned_policy = effective_policy
            return candidate
        n += 1


def validate_slug(slug: str, *, legacy: bool) -> str:
    # `--legacy` reserves the prefix (`00000`) for baseline waves/legacy artifacts, but it should not
    # impose additional semantics on the slug itself.
    if not SLUG_PATTERN.fullmatch(slug):
        raise ValueError("slug must contain only lowercase letters, digits, and dashes")
    return slug


def build_id(
    kind: str,
    slug: str,
    *,
    legacy: bool,
    timestamp: datetime | None = None,
    repo_root: Path | None = _UNSET,  # type: ignore[assignment]
    policy: tuple[datetime, int] | tuple[datetime, int, int, str] | None = None,
    commit: bool = True,
) -> str:
    """Build a full lifecycle ID. Passes ``commit`` through to
    ``next_available_prefix``; ``commit=False`` previews the ID without
    consuming the lifecycle slot (wave 1p3dk / 1p3ds)."""
    validated_slug = validate_slug(slug, legacy=legacy)
    if legacy:
        prefix = "00000"
    else:
        prefix = next_available_prefix(
            timestamp, policy=policy, repo_root=repo_root, commit=commit,
            kind=kind, slug=validated_slug,
        )
    if kind == "wave":
        # Waves use `{prefix} {slug}` with no `-wave` token.
        return f"{prefix} {validated_slug}"
    return f"{prefix}-{kind} {validated_slug}"


def build_timestamp(unix_seconds: int | None) -> datetime | None:
    if unix_seconds is None:
        return None
    if unix_seconds < 0:
        raise ValueError("unix seconds must be non-negative")
    return datetime.fromtimestamp(unix_seconds, tz=timezone.utc)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate shared lifecycle IDs for waves and changes.",
    )
    parser.add_argument("--kind", choices=("bug", "feat", "enh", "change", "doc", "debt", "ref", "task", "maint", "ops", "wave"), help="Lifecycle artifact type to generate.")
    parser.add_argument("--slug", help="Kebab-case topic slug to append to the generated ID.")
    parser.add_argument(
        "--legacy",
        action="store_true",
        help="Emit the reserved legacy prefix `00000` instead of the current generated lifecycle prefix.",
    )
    parser.add_argument(
        "--prefix-only",
        action="store_true",
        help=(
            "Print only the current generated base36 lifecycle prefix. Under scheme "
            "v2 this is the entropy-less base for the current day (kind/slug empty); "
            "actual mints additionally carry per-(kind, slug) hash entropy."
        ),
    )
    parser.add_argument(
        "--unix-seconds",
        type=int,
        help="Override the current UTC time with a specific Unix timestamp in seconds. Intended for deterministic tests and tooling.",
    )
    args = parser.parse_args(argv)

    if args.prefix_only:
        if args.slug or args.kind or args.legacy:
            parser.error("--prefix-only cannot be combined with --kind, --slug, or --legacy")
        return args

    if not args.kind or not args.slug:
        parser.error("--kind and --slug are required unless --prefix-only is used")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        timestamp = build_timestamp(args.unix_seconds)
        repo_root = discover_repo_root()
        if args.prefix_only:
            # --prefix-only is a low-level prefix utility, not a full ID mint, so
            # it does NOT emit the MCP-first reminder (wave 1p45b decision).
            print(build_prefix(timestamp))
            return 0

        # stdout stays the bare minted ID (machine-parseable); the MCP-first
        # nudge goes to stderr so it never pollutes a `$(...)` capture (wave 1p45b).
        print(build_id(args.kind, args.slug, legacy=args.legacy, timestamp=timestamp, repo_root=repo_root))
        print(
            "lifecycle_id: note — when the Wavefoundry MCP server is available, prefer the "
            "MCP minting tools (wave_new_<kind> / wf_create_wave); they dedupe against "
            "on-disk IDs. This CLI is the offline fallback.",
            file=sys.stderr,
        )
        return 0
    except ValueError as error:
        print(f"lifecycle_id: error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
