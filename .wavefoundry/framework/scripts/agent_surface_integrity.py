"""Read-only integrity inventory for canonical agent-role surfaces."""

from __future__ import annotations

from pathlib import Path
import re

from review_policy import REVIEW_POLICY_CARRIER_REGISTRY


# Same parse rule as ``wave_lint_lib.wave_validators._ROLE_RE`` (first ``Role:`` line
# anywhere in the document): the audit must group exactly the documents lint treats
# as role docs, so the two surfaces can never disagree about identity.
_ROLE = re.compile(r"^Role:\s+(.+)$", re.MULTILINE)
_CATEGORY = re.compile(r"^Category:\s+(.+)$", re.MULTILINE)
_EXEMPT = {"README.md", "session-handoff.md", "platform-mapping.md"}


def canonical_role_paths() -> dict[str, str]:
    """Return framework-owned role destinations from the policy registry."""
    result: dict[str, str] = {}
    for carrier in REVIEW_POLICY_CARRIER_REGISTRY:
        if carrier.owner != "renderer" or "executable_review" not in carrier.obligations:
            continue
        path = carrier.destination
        if not path.startswith("docs/agents/"):
            continue
        result[Path(path).stem] = path
    return result


def _metadata(text: str, pattern: re.Pattern[str]) -> str | None:
    match = pattern.search(text)
    return match.group(1).strip() if match else None


def _role_docs(root: Path) -> dict[str, list[dict[str, object]]]:
    agents = root / "docs" / "agents"
    grouped: dict[str, list[dict[str, object]]] = {}
    if not agents.is_dir():
        return grouped
    for path in sorted(agents.rglob("*.md")):
        if path.name in _EXEMPT or "memory" in path.parts or "journals" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        role = _metadata(text, _ROLE)
        if not role:
            continue
        rel = path.relative_to(root).as_posix()
        grouped.setdefault(role, []).append({
            "path": rel,
            "category": _metadata(text, _CATEGORY),
            "has_executable_review_evidence": "wave:executable-review-evidence begin" in text,
        })
    return grouped


def audit_agent_surfaces(root: Path) -> dict[str, object]:
    """Return advisory-only duplicate framework-role findings."""
    canonical = canonical_role_paths()
    grouped = _role_docs(root)
    duplicates = []
    for role, docs in sorted(grouped.items()):
        if len(docs) < 2:
            continue
        canonical_path = canonical.get(role)
        if canonical_path:
            duplicates.append({"role": role, "canonical_path": canonical_path, "paths": docs,
                               "remediation": "merge project-authored content into the canonical document, repoint live routing, then retire the duplicate"})
    return {
        "available": True,
        "canonical_role_paths": canonical,
        "duplicate_roles": duplicates,
        "finding_count": len(duplicates),
        "advisory": True,
    }
