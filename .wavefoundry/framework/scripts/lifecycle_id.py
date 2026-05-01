#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


CROCKFORD_BASE32_ALPHABET = "0123456789abcdefghjkmnpqrstvwxyz"
DEFAULT_EPOCH_UTC = datetime(2020, 2, 2, 2, 2, tzinfo=timezone.utc)
SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


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


def encode_crockford_base32(value: int) -> str:
    if value < 0:
        raise ValueError("value must be non-negative")
    if value == 0:
        return "0"

    encoded: list[str] = []
    remaining = value
    while remaining > 0:
        remaining, digit = divmod(remaining, 32)
        encoded.append(CROCKFORD_BASE32_ALPHABET[digit])
    return "".join(reversed(encoded))


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


def build_prefix(
    timestamp: datetime | None = None,
    *,
    policy: tuple[datetime, int] | None = None,
) -> str:
    current_time = (timestamp or current_utc_time()).astimezone(timezone.utc)
    epoch, hour_offset = policy if policy is not None else load_lifecycle_policy()
    elapsed_hours = int((current_time - epoch).total_seconds() // 3600) + hour_offset
    if elapsed_hours < 0:
        raise ValueError(
            f"timestamp must not be earlier than the configured lifecycle epoch ({epoch.isoformat().replace('+00:00', 'Z')}) "
            f"after applying hour_offset ({hour_offset})",
        )
    minute_bucket = (current_time.minute + 1) // 2
    return encode_crockford_base32(elapsed_hours).rjust(4, "0") + CROCKFORD_BASE32_ALPHABET[minute_bucket]


def validate_slug(slug: str, *, legacy: bool) -> str:
    # `--legacy` reserves the prefix (`00000`) for baseline waves/legacy artifacts, but it should not
    # impose additional semantics on the slug itself.
    if not SLUG_PATTERN.fullmatch(slug):
        raise ValueError("slug must contain only lowercase letters, digits, and dashes")
    return slug


def build_id(kind: str, slug: str, *, legacy: bool, timestamp: datetime | None = None) -> str:
    validated_slug = validate_slug(slug, legacy=legacy)
    prefix = "00000" if legacy else build_prefix(timestamp)
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
        help="Print only the current generated Crockford lifecycle prefix.",
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
        if args.prefix_only:
            print(build_prefix(timestamp))
            return 0

        print(build_id(args.kind, args.slug, legacy=args.legacy, timestamp=timestamp))
        return 0
    except ValueError as error:
        print(f"lifecycle_id: error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
