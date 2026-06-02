#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


BASE36_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"
DEFAULT_EPOCH_UTC = datetime(2020, 2, 2, 2, 2, tzinfo=timezone.utc)
SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")

# In-process floor: tracks the last prefix assigned in this process so rapid
# same-second calls produce unique prefixes before the filesystem scan sees the
# earlier write.  Subprocess invocations always start with None (fresh module).
_last_assigned_prefix: str | None = None


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


def load_lifecycle_policy(repo_root: Path | None = None) -> tuple[datetime, int]:
    """Return (epoch_utc, hour_offset) from docs/workflow-config.json when present; else defaults."""
    root = repo_root or discover_repo_root()
    default: tuple[datetime, int] = (DEFAULT_EPOCH_UTC, 0)
    if root is None:
        return default
    cfg = root / "docs" / "workflow-config.json"
    if not cfg.is_file():
        return default
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default
    policy = data.get("lifecycle_id_policy")
    if not isinstance(policy, dict):
        return default
    epoch: datetime
    epoch_raw = policy.get("epoch_utc")
    if isinstance(epoch_raw, str) and epoch_raw.strip():
        epoch = parse_epoch_utc(epoch_raw)
    else:
        epoch = DEFAULT_EPOCH_UTC
    hour_offset = policy.get("hour_offset", 0)
    if isinstance(hour_offset, bool) or not isinstance(hour_offset, int):
        raise ValueError("workflow-config lifecycle_id_policy.hour_offset must be a non-negative integer")
    if hour_offset < 0:
        raise ValueError("workflow-config lifecycle_id_policy.hour_offset must be non-negative")
    return epoch, hour_offset


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


# Wave 131bt close-out (131bu): integer-packed 5-minute-bucket encoding.
#
# Prior scheme appended ``BASE36[elapsed_minutes % 36]`` as the tail char, which
# wraps every 36 minutes — breaking the "lex order = creation order" guarantee.
# New scheme packs ``(days_since_epoch * 288 + bucket_5min) mod 36^5`` as a
# single base36 number, padded to 5 chars. Lex order matches wall-clock order
# across any day boundary within the 36^5 / 288 = 209,952 day (~575 year) horizon.
#
# 5-minute buckets (288 per day) align with whole-minute boundaries and whole-
# second boundaries (300 sec each); divide 36^5 cleanly with zero wasted slots
# (60,466,176 / 288 = 209,952 exact). The build suffix used by build_pack.py is
# the last 4 chars of this prefix — single source of truth for both encodings.
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


def build_prefix(
    timestamp: datetime | None = None,
    *,
    policy: tuple[datetime, int] | None = None,
) -> str:
    """Return the 5-character base36 lifecycle prefix for ``timestamp`` (default: now UTC).

    Encodes ``(days_since_epoch * 288 + bucket_5min) mod 36^5`` as base36, right-padded
    to 5 characters. Lex order matches wall-clock order within any 575-year window;
    builds within the same 5-minute window produce identical prefixes.

    ``policy`` is ``(epoch_utc, hour_offset)``; ``hour_offset`` is applied as
    ``hour_offset * 12`` additional buckets so existing config files with non-zero
    ``hour_offset`` continue to shift the encoding monotonically rather than by
    a different scale.
    """
    current_time = (timestamp or current_utc_time()).astimezone(timezone.utc)
    epoch, hour_offset = policy if policy is not None else load_lifecycle_policy()
    hour_offset_buckets = hour_offset * (60 // _BUCKET_WIDTH_MIN)  # hour_offset hours → buckets
    packed = _packed_value(current_time, epoch, hour_offset_buckets)
    return encode_base36(packed).rjust(5, "0")


_PREFIX_RE = re.compile(r"^([0-9a-z]{5})[-\s]")


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
    return prefixes


def next_available_prefix(
    timestamp: datetime | None = None,
    *,
    policy: tuple[datetime, int] | None = None,
    repo_root: Path | None = None,
) -> str:
    global _last_assigned_prefix
    base = build_prefix(timestamp, policy=policy)
    existing = _existing_prefixes(repo_root) if repo_root is not None else set()

    # Start from the greater of the time-based prefix and one past the last
    # in-process assignment.  This prevents rapid same-second calls from
    # returning identical prefixes before the earlier directory write is visible
    # to the filesystem scan.
    start_n = decode_base36(base)
    if _last_assigned_prefix is not None:
        last_n = decode_base36(_last_assigned_prefix)
        if last_n >= start_n:
            start_n = last_n + 1

    n = start_n
    while True:
        candidate = encode_base36(n).rjust(5, "0")
        if candidate not in existing:
            _last_assigned_prefix = candidate
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
    repo_root: Path | None = None,
    policy: tuple[datetime, int] | None = None,
) -> str:
    validated_slug = validate_slug(slug, legacy=legacy)
    if legacy:
        prefix = "00000"
    else:
        prefix = next_available_prefix(timestamp, policy=policy, repo_root=repo_root)
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
        help="Print only the current generated base36 lifecycle prefix.",
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
            print(build_prefix(timestamp))
            return 0

        print(build_id(args.kind, args.slug, legacy=args.legacy, timestamp=timestamp, repo_root=repo_root))
        return 0
    except ValueError as error:
        print(f"lifecycle_id: error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
