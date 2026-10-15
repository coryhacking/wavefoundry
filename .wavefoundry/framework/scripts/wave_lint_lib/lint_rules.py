"""Optional literal exclusions for generic documentation checks only."""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from contained_files import read_contained_bytes
from .constants import ADDITIONAL_REQUIRED_DOCS, PROMPT_SURFACE_FILES
from .helpers import _ENTRY_FILES, read_doc_text, relative_to_root, resolve_record_roots

RULES_PATH = "docs/lint-rules.toml"
MAX_RULES_BYTES = 64 * 1024
MAX_PATHS = 512
MAX_PATH_LENGTH = 4096


@dataclass(frozen=True)
class LintRules:
    paths: tuple[str, ...] = ()
    protected_files: frozenset[str] = frozenset()
    protected_trees: tuple[str, ...] = ()

    def excludes(self, root: Path, path: Path) -> bool:
        rel = relative_to_root(root, path)
        if rel in self.protected_files or any(rel.startswith(p) for p in self.protected_trees):
            return False
        return any(rel.startswith(p) if p.endswith("/") else rel == p for p in self.paths)

    def skip_generic_checks(self, root: Path, path: Path) -> bool:
        if not self.excludes(root, path):
            return False
        # Exclusion is not a safe-read exemption. Preserve the bounded reader's
        # refusal reporting for unreadable files and swaps after discovery.
        read_doc_text(root, path)
        return True


def load_lint_rules(root: Path) -> LintRules:
    """Read once per invocation; malformed input grants no partial exemptions."""
    try:
        raw = read_contained_bytes(root, root / RULES_PATH, max_bytes=MAX_RULES_BYTES, follow_links=False)
    except FileNotFoundError:
        return LintRules()
    except (OSError, ValueError, RuntimeError):
        raise ValueError(f"{RULES_PATH}: cannot read rules (requires a regular, unlinked file of at most 64 KiB)") from None
    try:
        data = tomllib.loads(raw.decode("utf-8"))
    except (ValueError, RecursionError, MemoryError):
        raise ValueError(f"{RULES_PATH}: invalid UTF-8 TOML") from None
    if set(data) - {"exclude"}:
        raise ValueError(f"{RULES_PATH}: only [exclude] is supported")
    exclude = data.get("exclude", {})
    if not isinstance(exclude, dict) or set(exclude) - {"paths"}:
        raise ValueError(f"{RULES_PATH}: [exclude] supports only paths")
    paths = exclude.get("paths", [])
    if not isinstance(paths, list) or len(paths) > MAX_PATHS:
        raise ValueError(f"{RULES_PATH}: exclude.paths must be an array of at most {MAX_PATHS} paths")
    for index, value in enumerate(paths):
        if (not isinstance(value, str) or not value or len(value) > MAX_PATH_LENGTH
                or any(ord(c) < 32 or 127 <= ord(c) <= 159 for c in value)
                or any(c in value for c in "\\:*?[]{}")
                or value.startswith("/")
                or any(part in {"", ".", ".."} for part in value.removesuffix("/").split("/"))):
            raise ValueError(f"{RULES_PATH}: exclude.paths[{index}] must be a literal repository-relative POSIX path (file or trailing-slash folder)")
    if not paths:
        return LintRules()
    roots = resolve_record_roots(root)
    if roots is None:
        raise ValueError(f"{RULES_PATH}: invalid record layout; exclusions not applied")
    from review_policy import review_policy_carriers
    from render_agent_surfaces import review_protocol_carriers

    protected = set(PROMPT_SURFACE_FILES) | set(ADDITIONAL_REQUIRED_DOCS) | set(_ENTRY_FILES)
    protected.update(carrier.destination for carrier in review_policy_carriers())
    protected.update(carrier.destination for carrier in review_protocol_carriers(root))
    protected.discard("docs/README.md")  # Still required to exist; project-owned navigation is excludable.
    trees = ["docs/prompts/", "docs/agents/"]
    for directory in (roots.waves, roots.plans, roots.archive):
        if directory is not None:
            trees.append(relative_to_root(root, directory).rstrip("/") + "/")
    return LintRules(tuple(paths), frozenset(protected), tuple(trees))
