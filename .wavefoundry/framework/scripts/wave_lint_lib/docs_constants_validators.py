"""Docs-vs-code constants lint (wave 1seax / 1seau).

Declarative checks binding DOCUMENTED facts to their owning code constants so
drifted claims fail the docs gate instead of waiting for the next external
review. Two sources feed the checks:

* the canonical ``public_contract`` module (vocabularies) — imported directly
  (tiny, side-effect-free);
* module-owned scalar constants (model names, format versions) — extracted by
  targeted AST parse of the OWNING module source, never by importing the heavy
  module and never by regex over scattered literals.

Also home to the scaffolding-integrity rules (1seau AC-5): admitted change
docs must carry a truthful ``Wave:`` reference, and wave records must not use
unbracketed pre-approval signoff phrasing. Both rules scope to NON-closed
waves — closed waves are history.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]


def _module_constant(rel_script: str, name: str) -> str | None:
    """AST-extract a top-level string-constant assignment from a script."""
    path = _SCRIPTS_DIR / rel_script
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        return node.value.value
    return None


def _public_contract():
    import sys
    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))
    import public_contract
    return public_contract


# Declarative claim table: (doc rel path, human label, capture regex,
# expected-value callable). The regex's group(1) must equal the expected value.
# A missing claim is itself a failure: the refreshed docs carry these facts in
# a stable, checkable form, and silently dropping one is drift too.
def _claims():
    pc = _public_contract()
    return (
        (
            "docs/architecture/performance-budget.md",
            "docs embedding model",
            re.compile(r"docs embedding model `([^`]+)`"),
            lambda: _module_constant("indexer.py", "DOCS_MODEL"),
        ),
        (
            "docs/architecture/performance-budget.md",
            "code embedding model",
            re.compile(r"code embedding model `([^`]+)`"),
            lambda: _module_constant("indexer.py", "CODE_MODEL"),
        ),
        (
            "docs/architecture/performance-budget.md",
            "reranker model",
            re.compile(r"reranker model `([^`]+)`"),
            lambda: _module_constant("indexer.py", "RERANKER_MODEL"),
        ),
        (
            "docs/RELIABILITY.md",
            "index_build content values",
            re.compile(r"index_build content values: `([^`]+)`"),
            lambda: "/".join(pc.INDEX_BUILD_CONTENT_VALUES),
        ),
        (
            "docs/RELIABILITY.md",
            "index_freshness states",
            re.compile(r"index_freshness states: `([^`]+)`"),
            lambda: "/".join(pc.INDEX_FRESHNESS_STATES),
        ),
        (
            "docs/RELIABILITY.md",
            "state-store schema version",
            re.compile(r"state-store schema version `([^`]+)`"),
            lambda: _module_constant("index_state_store.py", "STATE_STORE_SCHEMA_VERSION"),
        ),
        (
            "docs/RELIABILITY.md",
            "graph builder version",
            re.compile(r"graph builder version `([^`]+)`"),
            lambda: _module_constant("graph_indexer.py", "GRAPH_BUILDER_VERSION"),
        ),
        (
            "docs/architecture/performance-budget.md",
            "chunker version",
            re.compile(r"chunker version `([^`]+)`"),
            lambda: _module_constant("chunker.py", "CHUNKER_VERSION"),
        ),
    )


def check_docs_constants(root: Path) -> list[str]:
    """Assert documented facts match their owning code constants."""
    failures: list[str] = []
    for rel, label, pattern, expected_fn in _claims():
        doc = root / rel
        if not doc.is_file():
            continue  # target repos without the doc are out of scope
        try:
            text = doc.read_text(encoding="utf-8")
        except OSError:
            continue
        expected = expected_fn()
        if expected is None:
            failures.append(
                f"ERROR: {rel}: docs-constants check cannot resolve the code constant "
                f"for '{label}' — the owning module's constant moved or was renamed; "
                "update wave_lint_lib/docs_constants_validators.py"
            )
            continue
        m = pattern.search(text)
        if not m:
            failures.append(
                f"ERROR: {rel}: expected the documented fact '{label}' "
                f"(pattern {pattern.pattern!r}); the claim is missing — documented "
                "facts bound to code constants must not be silently dropped"
            )
            continue
        if m.group(1) != expected:
            line = text.count("\n", 0, m.start()) + 1
            failures.append(
                f"ERROR: {rel}:{line}: documented {label} `{m.group(1)}` does not "
                f"match the code constant `{expected}`"
            )
    return failures


_WAVE_FIELD_RE = re.compile(r"^Wave:\s*(.+?)\s*$", re.MULTILINE)
_SIGNOFF_LINE_RE = re.compile(r"^-\s*operator-signoff:\s*(.+?)\s*$", re.MULTILINE)
_UNBRACKETED_PREAPPROVAL_RE = re.compile(
    r"^approved\s+(when|if|once|after)\b", re.IGNORECASE
)
_STATUS_RE = re.compile(r"^Status:\s*(\w+)", re.MULTILINE)


def check_wave_scaffolding_integrity(root: Path) -> list[str]:
    """1seau AC-5: Wave-reference integrity on admitted docs; no unbracketed
    pre-approval signoff phrasing in wave records. Non-closed waves only."""
    failures: list[str] = []
    waves_root = root / "docs" / "waves"
    if not waves_root.is_dir():
        return failures
    for wave_dir in sorted(waves_root.iterdir()):
        wave_md = wave_dir / "wave.md"
        if not wave_dir.is_dir() or not wave_md.is_file():
            continue
        try:
            wave_text = wave_md.read_text(encoding="utf-8")
        except OSError:
            continue
        status_m = _STATUS_RE.search(wave_text)
        if status_m and status_m.group(1).lower() == "closed":
            continue  # history
        # (b) unbracketed pre-approval signoff phrasing in the wave record.
        for m in _SIGNOFF_LINE_RE.finditer(wave_text):
            value = m.group(1)
            if value.startswith("<"):
                continue  # the bracketed placeholder is the load-bearing convention
            if _UNBRACKETED_PREAPPROVAL_RE.match(value):
                line = wave_text.count("\n", 0, m.start()) + 1
                failures.append(
                    f"ERROR: {wave_md.relative_to(root).as_posix()}:{line}: "
                    f"unbracketed pre-approval signoff phrasing '{value}' — the close "
                    "gate reads an unbracketed leading 'approved' as authorization; "
                    "use the bracketed placeholder `<approved when operator confirms "
                    "closure>` until the operator actually approves"
                )
        # (a) admitted change docs: truthful Wave: reference.
        for doc in sorted(wave_dir.glob("*.md")):
            if doc.name == "wave.md":
                continue
            try:
                doc_text = doc.read_text(encoding="utf-8")
            except OSError:
                continue
            m = _WAVE_FIELD_RE.search(doc_text)
            if not m:
                continue  # absence handled by scaffold checks
            value = m.group(1).strip().strip("`")
            rel = doc.relative_to(root).as_posix()
            if value.upper() == "TBD":
                line = doc_text.count("\n", 0, m.start()) + 1
                failures.append(
                    f"ERROR: {rel}:{line}: admitted change doc still says 'Wave: TBD' — "
                    f"set it to `{wave_dir.name}`"
                )
            elif value != wave_dir.name and not wave_dir.name.startswith(value):
                line = doc_text.count("\n", 0, m.start()) + 1
                failures.append(
                    f"ERROR: {rel}:{line}: 'Wave: {value}' does not match the containing "
                    f"wave directory `{wave_dir.name}`"
                )
    return failures
