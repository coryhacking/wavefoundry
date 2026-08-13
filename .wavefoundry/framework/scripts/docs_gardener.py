#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path


sys.dont_write_bytecode = True

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import venv_bootstrap  # the single venv resolver (wave 1p7pl)
import subprocess_util  # shared subprocess isolation (wave 1p8gu)
import cli_stdio  # shared UTF-8 stdio reconfigure (wave 1p8gv)

# Activate the shared tool venv IN-PROCESS before any heavy work (wave 1p7pl/1p802). No-op when
# already in the venv or when it does not exist yet (fresh bootstrap).
venv_bootstrap.activate_tool_venv()
# Wave 1p8gv: CLI entry — UTF-8 stdout/stderr so non-ASCII prints never raise on a cp1252 console.
cli_stdio.configure_utf8_stdio()

LAST_VERIFIED_PATTERN = re.compile(r"^(Last verified:\s+)(\d{4}-\d{2}-\d{2})$", re.MULTILINE)


def project_root() -> Path:
    """Return the project root from ``PROJECT_ROOT`` env var or CWD.

    Intentional differences from the copies in other scripts:
    - Only reads ``PROJECT_ROOT`` (not ``REPO_ROOT``) — the gardener is always
      invoked with an explicit env var or from the correct working directory.
    - Does not walk up the directory tree; relies on the caller to set the env.
    - Never returns ``None``.

    Cross-reference: ``server._discover_root``, ``indexer._discover_root``,
    ``lifecycle_id.discover_repo_root``, ``render_platform_surfaces.discover_repo_root``.
    A future consolidation task should unify these into a shared utility.
    """
    env_root = os.environ.get("PROJECT_ROOT")
    return (Path(env_root) if env_root else Path.cwd()).resolve()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Wave Framework docs gardener")
    parser.add_argument("--date", required=False, help="YYYY-MM-DD date override (defaults to today)")
    parser.add_argument(
        "--paths",
        nargs="+",
        metavar="REL_PATH",
        help="Stamp Last verified on these specific docs instead of git-changed docs",
    )
    parser.add_argument(
        "--all-docs",
        action="store_true",
        help="Stamp Last verified on every docs/**/*.md file instead of git-changed docs",
    )
    return parser.parse_args(argv)


def validate_args(args: argparse.Namespace) -> None:
    if args.all_docs and args.paths:
        raise SystemExit("docs-gardener: --all-docs and --paths are mutually exclusive")


def iter_markdown_docs(root: Path):
    docs_root = root / "docs"
    if not docs_root.exists():
        return
    for path in docs_root.rglob("*.md"):
        if path.is_file():
            yield path


def collect_changed_markdown_paths(root: Path) -> list[Path]:
    docs_root = root / "docs"
    if not docs_root.exists():
        return []
    try:
        proc = subprocess_util.isolated_run(
            ["git", "-C", str(root), "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0:
        return []
    out: list[Path] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line.endswith(".md"):
            continue
        candidate = (root / line).resolve()
        try:
            candidate.relative_to(docs_root.resolve())
        except ValueError:
            continue
        if candidate.is_file():
            out.append(candidate)
    return sorted(set(out))


def resolve_path_args(root: Path, rel_parts: list[str]) -> list[Path]:
    docs_root = (root / "docs").resolve()
    resolved: list[Path] = []
    for raw in rel_parts:
        p = (root / raw).resolve()
        try:
            p.relative_to(docs_root)
        except ValueError as exc:
            raise SystemExit(f"docs-gardener: path must be under docs/: {raw}") from exc
        if not p.is_file():
            raise SystemExit(f"docs-gardener: not a file: {raw}")
        if p.suffix.lower() != ".md":
            raise SystemExit(f"docs-gardener: expected markdown file: {raw}")
        resolved.append(p)
    return resolved


def resolve_metadata_targets(root: Path, args: argparse.Namespace) -> list[Path]:
    if args.all_docs:
        return sorted(iter_markdown_docs(root))
    if args.paths:
        return resolve_path_args(root, args.paths)
    return collect_changed_markdown_paths(root)


def refresh_last_verified(path: Path, date_value: str) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")
    updated = LAST_VERIFIED_PATTERN.sub(rf"\g<1>{date_value}", text, count=1)
    if updated != text:
        path.write_text(updated, encoding="utf-8")
        return True
    return False


def manifest_path(root: Path) -> Path:
    return root / "docs" / "prompts" / "prompt-surface-manifest.json"


def default_manifest_payload(date_value: str) -> dict:
    return {
        "schema_version": 1,
        "generated_artifacts": [
            "docs/prompts/prompt-surface-manifest.json",
            "docs/agents/session-handoff.md",
            "docs/waves/",
            "docs/waves/README.md",
            "docs/agents/personas/",
            "docs/agents/personas/README.md",
            "docs/reports/",
        ],
        "last_gardened_at": date_value,
        "public_prompt_surface": [],
        "seed_framework_source": ".wavefoundry/framework",
    }


# 1v7a0: keys whose CONTENT the framework owns, so an existing manifest is
# reconciled against `default_manifest_payload` rather than left as installed.
# Scoped deliberately: every other key in a real manifest has a live consumer
# outside this module (`wave_root` is read by wave_lint_lib, so clobbering it
# breaks docs-lint itself; `framework_revision` is read by check_version and
# dashboard_lib; `upgrade_merge_notes` is why reconcile_scan excludes this
# file), and a wholesale payload replacement would be a working-behaviour
# regression rather than a metadata refresh.
_FRAMEWORK_OWNED_MANIFEST_KEYS: tuple[str, ...] = ("generated_artifacts",)

# Entries retired from the framework that linger in installed manifests. The
# key itself is NOT removed: nothing in this repository reads
# `enabled_internal_features`, but a target repo or host integration might, and
# a manifest is the wrong place to prove a negative about out-of-tree readers.
# Pruning the retired VALUE fixes what is demonstrably wrong (the journal
# system is retired) without asserting more than was verified.
_RETIRED_MANIFEST_FEATURES: frozenset[str] = frozenset({"agent_journals"})


def reconcile_manifest_payload(data: dict, default: dict) -> dict:
    """Reconcile framework-owned manifest keys against *default*, in place.

    Drift runs in BOTH directions and both matter: an entry retired from the
    default lingers forever (the reported symptom), and an entry ADDED to the
    default never reaches a repository installed before it existed, which
    leaves the framework's own record of what it generates wrong. Assignment
    rather than a union fixes both; a union would only ever grow the list and
    could never retire an entry.

    Keys the default does not model are untouched.
    """

    for key in _FRAMEWORK_OWNED_MANIFEST_KEYS:
        if key in default:
            data[key] = default[key]
    features = data.get("enabled_internal_features")
    if isinstance(features, list):
        pruned = [f for f in features if f not in _RETIRED_MANIFEST_FEATURES]
        if pruned != features:
            data["enabled_internal_features"] = pruned
    return data


def normalize_manifest_json(data: dict) -> str:
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def ensure_manifest(
    root: Path,
    date_value: str,
    *,
    bump_last_gardened: bool,
) -> tuple[Path, bool]:
    path = manifest_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        payload = default_manifest_payload(date_value)
        path.write_text(normalize_manifest_json(payload), encoding="utf-8")
        return path, True
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = {}
    data.setdefault("schema_version", 1)
    data.setdefault("seed_framework_source", ".wavefoundry/framework")
    # 1v7a0: reconcile the framework-owned keys on EVERY run, not only when the
    # caller is bumping the date. `bump_last_gardened` is False precisely when
    # no doc needed stamping, which is the steady state of a well-gardened
    # repository — gating reconciliation on it meant the manifest healed only on
    # runs that happened to stamp something else, so a healthy repo drifted
    # forever. Found by a post-implementation review pass through the real
    # `gardener_run` entry point; the first implementation returned early here
    # and its AC-5 evidence came from calling `ensure_manifest` directly, which
    # bypassed that gate.
    #
    # The date stamp stays gated, so a non-bumping run still does not churn
    # `last_gardened_at`, and the change-only write below means a manifest that
    # needs neither reconciliation nor a stamp is not rewritten at all.
    reconcile_manifest_payload(data, default_manifest_payload(date_value))
    if bump_last_gardened:
        data["last_gardened_at"] = date_value
    new_text = normalize_manifest_json(data)
    old_text = path.read_text(encoding="utf-8")
    if new_text == old_text:
        return path, False
    path.write_text(new_text, encoding="utf-8")
    return path, True


def ensure_session_handoff(root: Path, date_value: str) -> tuple[Path, bool]:
    path = root / "docs" / "agents" / "session-handoff.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return path, False
    lines = [
        "# Session Handoff",
        "",
        "Owner: Engineering",
        "Status: generated",
        f"Last verified: {date_value}",
        "",
        "## Purpose",
        "",
        "Holds paused-work state for unfinished multi-step work.",
        "",
        "## Current State",
        "",
        "- No active handoff recorded.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path, True


def gardener_run(root: Path, args: argparse.Namespace) -> tuple[int, list[str]]:
    root = root.resolve()
    validate_args(args)
    date_value = args.date or date.today().isoformat()
    updated_paths: list[str] = []
    stamped_paths: list[str] = []

    targets = resolve_metadata_targets(root, args)
    for path in targets:
        if refresh_last_verified(path, date_value):
            rel = path.relative_to(root).as_posix()  # Wave 1p6dx: forward-slash rels in output
            updated_paths.append(rel)
            stamped_paths.append(rel)

    bump_manifest = bool(updated_paths)
    manifest_p, manifest_wrote = ensure_manifest(root, date_value, bump_last_gardened=bump_manifest)
    if manifest_wrote:
        updated_paths.append(manifest_p.relative_to(root).as_posix())  # Wave 1p6dx: forward-slash

    sh_path, sh_created = ensure_session_handoff(root, date_value)
    if sh_created:
        updated_paths.append(sh_path.relative_to(root).as_posix())  # Wave 1p6dx: forward-slash

    if not stamped_paths:
        print("docs-gardener: ok (nothing to report)")
        return 0, sorted(set(updated_paths))

    # Wave 1tbvo: no reindex report is written — nothing consumed the dated
    # files and every validator already exempted them. Stdout and the returned
    # list are the record of what was stamped; git history keeps the rest.
    # The per-path `docs-gardener: updated <path>` lines are a STABLE OUTPUT
    # CONTRACT parsed by run_garden() in server_impl.py — the MCP envelope's
    # updated/files_updated fields and the background index refresh depend on
    # them. Change both sides together.
    paths_for_body = sorted(set(updated_paths))
    for rel in paths_for_body:
        print(f"docs-gardener: updated {rel}")
    print(f"docs-gardener: stamped {len(stamped_paths)} doc(s)")
    return 0, paths_for_body


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    code, _paths = gardener_run(project_root(), args)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
