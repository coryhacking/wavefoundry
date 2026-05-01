from __future__ import annotations

import json
from pathlib import Path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def load_json(path: Path) -> tuple[dict[str, object] | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as exc:  # pragma: no cover - exercised by fixture failures if added later
        return None, str(exc)


def iter_markdown_docs(root: Path):
    docs_root = root / "docs"
    if not docs_root.exists():
        return
    for path in docs_root.rglob("*.md"):
        if path.is_file():
            yield path


# Agent entry files that live outside docs/ but carry relative links worth checking.
_ENTRY_FILES = ("AGENTS.md", "CLAUDE.md", "WARP.md")


def iter_linkable_docs(root: Path):
    """Yield all markdown files subject to link checking.

    Covers docs/**/*.md plus the agent entry files at the repo root.
    """
    yield from iter_markdown_docs(root)
    for name in _ENTRY_FILES:
        path = root / name
        if path.is_file():
            yield path


def relative_to_root(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def write_if_changed(path: Path, content: str) -> bool:
    existing = path.read_text(encoding="utf-8") if path.exists() else None
    if existing == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True