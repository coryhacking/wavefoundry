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
            "docs/agents/journals/",
            "docs/agents/journals/README.md",
            "docs/agents/personas/",
            "docs/agents/personas/README.md",
            "docs/reports/",
        ],
        "last_gardened_at": date_value,
        "public_prompt_surface": [],
        "seed_framework_source": ".wavefoundry/framework",
    }


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
    if not bump_last_gardened:
        return path, False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = {}
    data.setdefault("schema_version", 1)
    data.setdefault("seed_framework_source", ".wavefoundry/framework")
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


def render_report(date_value: str, updated_paths: list[str]) -> str:
    lines = [
        "# Reindex Report",
        "",
        "Owner: Engineering",
        "Status: generated",
        f"Last verified: {date_value}",
        "Verification method: `.wavefoundry/framework/scripts/docs_gardener.py`.",
        "",
        "## Updated Paths",
        "",
    ]
    if updated_paths:
        lines.extend([f"- `{path}`" for path in sorted(updated_paths)])
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Stamps `Last verified:` on git-changed docs under `docs/` and refreshes this report.",
            "- Use `--paths <doc> [...]` to stamp specific files; use `--all-docs` for a full sweep.",
            "- Pass `--date <YYYY-MM-DD>` only when overriding today's date.",
        ]
    )
    return "\n".join(lines) + "\n"


def gardener_run(root: Path, args: argparse.Namespace) -> tuple[int, list[str]]:
    root = root.resolve()
    validate_args(args)
    date_value = args.date or date.today().isoformat()
    updated_paths: list[str] = []
    stamped_paths: list[str] = []

    targets = resolve_metadata_targets(root, args)
    for path in targets:
        if refresh_last_verified(path, date_value):
            rel = path.relative_to(root).as_posix()  # Wave 1p6dx: forward-slash in the reindex report
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

    report_rel = f"docs/reports/reindex-{date_value}.md"
    report_path = root / report_rel
    report_path.parent.mkdir(parents=True, exist_ok=True)
    paths_for_body = sorted(set(updated_paths))
    content = render_report(date_value, paths_for_body)
    need_write = not report_path.exists() or report_path.read_text(encoding="utf-8") != content
    if need_write:
        paths_for_body = sorted(set(updated_paths + [report_rel]))
        content = render_report(date_value, paths_for_body)
        report_path.write_text(content, encoding="utf-8")
        print(f"docs-gardener: wrote {report_path.relative_to(root)}")
    else:
        print(f"docs-gardener: ok ({report_path.relative_to(root)} unchanged)")

    return 0, paths_for_body


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    code, _paths = gardener_run(project_root(), args)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
