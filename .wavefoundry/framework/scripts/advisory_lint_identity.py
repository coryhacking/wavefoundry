"""Content identity for advisory trigger reuse; no validation result or storage."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from contained_files import read_contained_bytes

INCREMENTAL_FULL_FALLBACK_FILES = (
    "docs/workflow-config.json",
    "docs/prompts/prompt-surface-manifest.json",
    "docs/repo-profile.json",
)

ADVISORY_IDENTITY_MAX_FILE_BYTES = 8 * 1024 * 1024
ADVISORY_IDENTITY_MAX_FILES = 2048
ADVISORY_IDENTITY_MAX_TOTAL_BYTES = 64 * 1024 * 1024

# This helper is cached by ordinary Python imports. Bind the executing module
# code to the installed bytes, as index_compatibility does for index producers;
# that producer-only registry deliberately does not own advisory lint modules.
try:
    _LOADED_SOURCE = read_contained_bytes(Path(__file__).resolve().parent, Path(__file__), max_bytes=ADVISORY_IDENTITY_MAX_FILE_BYTES)
    _LOADED_SOURCE_CURRENT = sys._getframe().f_code == compile(_LOADED_SOURCE, __file__, "exec", dont_inherit=True, optimize=sys.flags.optimize)
except (OSError, RuntimeError, ValueError, SyntaxError):
    _LOADED_SOURCE = None
    _LOADED_SOURCE_CURRENT = False


def _inventory(base: Path, relative: str, *, python_only: bool = False) -> list[Path]:
    directory = base / relative
    if directory.is_symlink():
        raise OSError("linked rule directory")
    if not directory.exists():
        return []
    if not directory.is_dir():
        raise OSError("rule tree is not a directory")
    paths = []
    visited = 0
    def refused(error):
        raise error
    for parent, dirs, files in os.walk(directory, onerror=refused, followlinks=False):
        visited += 1
        if visited + len(paths) > ADVISORY_IDENTITY_MAX_FILES:
            raise OSError("rule inventory exceeds advisory bound")
        dirs[:] = [name for name in dirs if name not in {"tests", "__pycache__", ".pytest_cache"}]
        if any((Path(parent) / name).is_symlink() for name in dirs):
            raise OSError("linked rule directory")
        for name in files:
            path = Path(parent) / name
            if not python_only or path.suffix == ".py":
                paths.append(path)
                if len(paths) > ADVISORY_IDENTITY_MAX_FILES:
                    raise OSError("rule inventory exceeds advisory bound")
    return sorted(paths)


def advisory_lint_identity(root: Path, scripts_dir: Path) -> str | None:
    """Bind exact triggers, actual rule sources/assets, root and scope semantics.

    The rule set deliberately includes every shipped Python module (excluding
    tests) rather than maintaining a fragile import allowlist. Filesystem names
    and absent optional inputs participate; timestamps never establish identity.
    Unreadable or linked inputs decline reuse. Callers compare snapshots around
    execution; an identity alone is not provenance for a successful full scan.
    """
    try:
        if not _LOADED_SOURCE_CURRENT or read_contained_bytes(Path(__file__).resolve().parent, Path(__file__), max_bytes=ADVISORY_IDENTITY_MAX_FILE_BYTES) != _LOADED_SOURCE:
            return None
        root = root.resolve(strict=True)
        scripts_dir = scripts_dir.resolve(strict=True)
        source = scripts_dir.parent
        rule_paths = _inventory(source, scripts_dir.name, python_only=True)
        if not (scripts_dir / "docs_lint.py").is_file():
            return None
        inputs = [("rule:" + path.relative_to(source).as_posix(), source, path) for path in rule_paths]
        inputs.extend(("root:" + rel, root, root / rel) for rel in INCREMENTAL_FULL_FALLBACK_FILES)
        # Scanner rules are executable validation inputs outside the Python tree.
        for rel in ("docs/scan-rules.toml", ".wavefoundry/framework/scan-rules.toml", ".wavefoundry/framework/scan-allowlist"):
            inputs.append(("root:" + rel, root, root / rel))
        inputs.extend(("rule-asset:" + name, source, source / name) for name in ("VERSION", "scan-rules.toml", "scan-allowlist"))
        # Full validators compare manifests, carrier templates and seeds too.
        # Inventory both installed target assets and the executing source fallback.
        trees = []
        for label, owner, prefix in (("source", source, ""), ("target", root, ".wavefoundry/framework/")):
            inputs.append((label + ":VERSION", owner, owner / (prefix + "VERSION")))
            for relative in ("seeds", "install", "docs"):
                directory = prefix + relative
                paths = _inventory(owner, directory)
                trees.append((label + ":" + directory, (owner / directory).exists(), [path.relative_to(owner).as_posix() for path in paths]))
                inputs.extend((label + ":" + path.relative_to(owner).as_posix(), owner, path) for path in paths)
        if len(inputs) > ADVISORY_IDENTITY_MAX_FILES:
            return None
        values = []
        total_bytes = 0
        for name, owner, path in inputs:
            if path.is_symlink():
                return None
            try:
                content = read_contained_bytes(owner, path, max_bytes=ADVISORY_IDENTITY_MAX_FILE_BYTES)
            except FileNotFoundError:
                if path.exists():
                    return None
                values.append((name, None))
            else:
                total_bytes += len(content)
                if total_bytes > ADVISORY_IDENTITY_MAX_TOTAL_BYTES:
                    return None
                values.append((name, hashlib.sha256(content).hexdigest()))
        payload = {
            "root": str(root), "rules_root": str(scripts_dir), "inputs": values,
            "scope": "docs_lint:changed:per-file-and-existing-dependencies:scan_all=false:v1",
            "triggers": INCREMENTAL_FULL_FALLBACK_FILES,
            "trees": trees,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    except (OSError, RuntimeError, ValueError):
        return None
