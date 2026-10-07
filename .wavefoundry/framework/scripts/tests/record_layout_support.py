"""Test support for the record-layout constants (wave 1y0gz).

The layout is defined by module constants in ``record_paths`` (no runtime
configuration), so a test that wants a relocated or nested layout patches the
constants. Two forms:

* :func:`patch_layout` / :func:`apply_layout` for in-process tests. Every
  loaded copy of ``record_paths`` is patched (the server support loader may
  hold its own module object), and the docs-lint root cache is cleared.
* :func:`run_script_with_layout` for subprocess CLI tests (docs-lint, the
  gardener): the constants are set in the child before the script runs.

Profiles (wave 1zim5, change 1zim1). A profile asset under
``tests/fixtures/profiles/<name>.json`` names fork-editable constants per
module; :func:`apply_profile` writes them into a COPIED scripts tree the way a
fork edits it at merge time. :class:`RecordTreeBuilder` and
:func:`localized_docs_lint_fixture` write records the way a profile expects,
and :func:`default_profile_only` marks a test whose subject is the default
profile. A profile may also declare distribution tool extensions in
``mcp_tool_extensions`` (change 1zim4); those never change the profile the
marker sees.

The expected profile (change 1zima). :func:`expected_profile` resolves which
profile the loaded constants must be: the single asset marked
``"active": true`` (a distribution's own), else the shipped defaults, with
the asset named by ``WAVEFOUNDRY_TEST_PROFILE`` (the run mode) overlaid on
top. It is the one reader of that variable. :func:`expected_profile_mismatch`
compares the loaded record constants with it exactly. This module is test
support: production code never imports it.
"""
from __future__ import annotations

import contextlib
import dataclasses
import functools
import json
import os
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parents[1]

_KEYS = {"waves_root": "WAVES_ROOT", "plans_root": "PLANS_ROOT", "nested": "NESTED", "max_depth": "MAX_DEPTH",
         "archive_root": "ARCHIVE_ROOT"}


def _record_paths_modules(extra: tuple[Any, ...] = ()) -> list[Any]:
    found: list[Any] = []
    for name, mod in list(sys.modules.items()):
        if mod is not None and (name == "record_paths" or name.endswith(".record_paths")):
            found.append(mod)
    for mod in extra:
        if mod is not None:
            found.append(mod)
    if not found:
        import record_paths  # noqa: WPS433 (test support)

        found.append(record_paths)
    return list(dict.fromkeys(found))


def _values(**kwargs: Any) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, attr in _KEYS.items():
        if key in kwargs:
            out[attr] = kwargs[key]
    return out


def _clear_lint_cache() -> None:
    for name, mod in list(sys.modules.items()):
        if mod is not None and name.endswith("wave_lint_lib.helpers"):
            clear = getattr(mod, "read_text_cache_clear", None)
            if clear is not None:
                clear()


@contextlib.contextmanager
def patch_layout(*, modules: tuple[Any, ...] = (), **kwargs: Any):
    """Patch ``WAVES_ROOT`` / ``PLANS_ROOT`` / ``NESTED`` / ``MAX_DEPTH`` on
    every loaded ``record_paths`` (plus ``modules``) for the block."""
    values = _values(**kwargs)
    with contextlib.ExitStack() as stack:
        for mod in _record_paths_modules(modules):
            for attr, value in values.items():
                stack.enter_context(mock.patch.object(mod, attr, value))
        _clear_lint_cache()
        try:
            yield
        finally:
            _clear_lint_cache()


def apply_layout(testcase: Any, *, modules: tuple[Any, ...] = (), **kwargs: Any) -> None:
    """``patch_layout`` bound to a ``TestCase``'s cleanup."""
    cm = patch_layout(modules=modules, **kwargs)
    cm.__enter__()
    testcase.addCleanup(cm.__exit__, None, None, None)


def layout_prelude(**kwargs: Any) -> str:
    """Python source that sets the constants in a fresh interpreter."""
    lines = [
        "import sys",
        f"sys.path.insert(0, {str(SCRIPTS_DIR)!r})",
        "import record_paths as _rp",
    ]
    for attr, value in _values(**kwargs).items():
        lines.append(f"_rp.{attr} = {value!r}")
    return "\n".join(lines)


def run_script_with_layout(
    script: Path, args: list[str], *, layout: dict[str, Any], cwd: Path | None = None, env: dict | None = None
) -> subprocess.CompletedProcess[str]:
    """Run ``script`` as ``__main__`` in a child interpreter whose
    ``record_paths`` constants are set to ``layout`` first."""
    code = "\n".join(
        [
            layout_prelude(**layout),
            "import runpy",
            f"sys.argv = [{str(script)!r}] + {list(args)!r}",
            f"runpy.run_path({str(script)!r}, run_name='__main__')",
        ]
    )
    return subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=str(cwd) if cwd else None,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


# ---------------------------------------------------------------------------
# Profiles (wave 1zim5, change 1zim1)
# ---------------------------------------------------------------------------

PROFILES_DIR = SCRIPTS_DIR / "tests" / "fixtures" / "profiles"
DOCS_LINT_FIXTURE = SCRIPTS_DIR / "tests" / "fixtures" / "docs_lint" / "base"
# The modules a profile asset may edit, in the order they are applied.
PROFILE_MODULES = ("vocabulary_profile", "record_paths", "mcp_tool_extensions")
_PROFILE_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")

# The shipped default of every fork-editable constant, frozen here on purpose:
# a distribution edits the modules themselves, so comparing a module with its
# own values could never tell an edited tree from the shipped one. A new
# editable constant is added here too (a test pins these key sets to the
# modules' own name lists). Treat as read-only; the helpers below copy it.
_SHIPPED_VOCABULARY = {
    "CONTAINER_NAME": "Wave",
    "CONTAINER_NAME_PLURAL": "Waves",
    "ITEM_NAME": "Change",
    "ITEM_NAME_PLURAL": "Changes",
    "RECORD_FILENAME": "wave.md",
    "ID_KEY": "wave-id",
    "RECORD_TITLE": "# Wave Record",
    "SUMMARY_HEADING": "## Wave Summary",
    "MEMBER_HEADING": "## Changes",
    "MEMBER_ID_LABEL": "Change ID",
    "MEMBER_STATUS_LABEL": "Change Status",
    "BACKREF_LABEL": "Wave",
}
SHIPPED_DEFAULTS: "dict[str, dict[str, Any]]" = {
    "vocabulary_profile": {**_SHIPPED_VOCABULARY, "ARCHIVE_PROFILE": None, "EXTRA_CHANGE_KINDS": (),
                           # Wave 1zyb4 (1zxnw): the lifecycle prompt-name override.
                           "PROMPT_NAME_OVERRIDES": {}},
    "record_paths": {
        "WAVES_ROOT": "docs/waves",
        "PLANS_ROOT": "docs/plans",
        "NESTED": False,
        "MAX_DEPTH": 4,
        "ARCHIVE_ROOT": None,
    },
}

# The shipped (empty) value of every distribution-edited tool declaration in
# ``mcp_tool_extensions`` (change 1zim4), frozen like SHIPPED_DEFAULTS and
# pinned by a test to the module's own ``EXTENSION_*`` names. Tuple-typed
# constants stay tuples when a profile writes them. It is the base the
# declaration helper in ``declaration_support`` patches in, and it is kept
# apart from SHIPPED_DEFAULTS on purpose: a declaration changes the served
# tool surface, not the record vocabulary or layout, so it never makes the
# default-profile-only marker skip.
SHIPPED_DECLARATION: "dict[str, Any]" = {
    "EXTENSION_MODULES": (),
    # Wave 1zls8 (1zltx): declared helper modules.
    "EXTENSION_HELPER_MODULES": (),
    "EXTENSION_TOOL_PREFIXES": (),
    "EXTENSION_TOOL_TIERS": {},
    "EXTENSION_OVERRIDES": {},
    "EXTENSION_TOOL_ALIASES": {},
    "EXTENSION_TOOL_PARAMETERS": {},
    "EXTENSION_HIDDEN_TOOLS": (),
    "EXTENSION_REPLACEMENTS": {},
    # Wave 1zimf (1zimo): lock and artifact-credit declarations.
    "EXTENSION_LIFECYCLE_TOOLS": (),
    "EXTENSION_ARTIFACT_PATH_FIELDS": {},
    # Wave 1zv8c (1zv89): declared skills, read only by the renderer.
    "EXTENSION_SKILLS": {},
    # Wave 1zyb3 (1zxnv): the journal migration declaration, read only by the upgrade.
    "EXTENSION_JOURNAL_TEMPLATES": (),
    "EXTENSION_JOURNAL_PRE_MIGRATION_HOOK": "",
}
# Every constant a profile asset may name, per module.
_EDITABLE = {**SHIPPED_DEFAULTS, "mcp_tool_extensions": SHIPPED_DECLARATION}

# A fixed date keeps every builder output byte-stable across runs.
_FIXTURE_DATE = "2026-03-21"


class ProfileInvalid(ValueError):
    """A profile asset, or its application to a copied tree, is unusable."""


def profile_names(profiles_dir: "Path | None" = None) -> list[str]:
    """The profile assets in ``profiles_dir`` (default: the tests' own), by name."""
    directory = PROFILES_DIR if profiles_dir is None else Path(profiles_dir)
    return sorted(p.stem for p in directory.glob("*.json"))


def _module_file_errors(data: dict, profiles_dir: "Path | None") -> list[str]:
    """Problems with an asset's ``module_files`` (wave 1zyb3, change 1zxnu):
    ``{module_name: path relative to the profiles directory}``, each module
    declared in the asset's ``EXTENSION_MODULES`` or
    ``EXTENSION_HELPER_MODULES`` and each source an existing file."""
    if "module_files" not in data:
        return []
    files = data["module_files"]
    if not isinstance(files, dict) or not files:
        return ["'module_files' must be a non-empty object of module name to source path"]
    directory = PROFILES_DIR if profiles_dir is None else Path(profiles_dir)
    entry = data["modules"].get("mcp_tool_extensions")
    entry = entry if isinstance(entry, dict) else {}
    declared: set[str] = set()
    for name in ("EXTENSION_MODULES", "EXTENSION_HELPER_MODULES"):
        value = entry.get(name)
        if isinstance(value, (list, tuple)):
            declared.update(item for item in value if isinstance(item, str))
    errors: list[str] = []
    for module, rel in files.items():
        if not isinstance(module, str) or not module.isidentifier():
            errors.append(f"module_files key {module!r} must be a flat module name")
            continue
        if module not in declared:
            errors.append(f"module_files names {module!r}, which the asset's EXTENSION_MODULES or "
                          "EXTENSION_HELPER_MODULES does not declare")
        if (not isinstance(rel, str) or not rel or "\\" in rel or ":" in rel or rel.startswith("/")
                or any(part in ("", ".", "..") for part in rel.split("/"))):
            errors.append(f"module_files[{module!r}] must be a '/'-separated path inside the profiles "
                          f"directory, not {rel!r}")
            continue
        if not (directory / rel).is_file():
            errors.append(f"module_files[{module!r}]: no source file {rel} in {directory}")
    return errors


def _profile_errors(data: Any, profiles_dir: "Path | None" = None) -> list[str]:
    if not isinstance(data, dict) or not isinstance(data.get("modules"), dict) or not data["modules"]:
        return ["a profile needs a non-empty 'modules' object"]
    errors: list[str] = _module_file_errors(data, profiles_dir)
    if "active" in data and not isinstance(data["active"], bool):
        errors.append(f"'active' must be true or false, not {data['active']!r}")
    for module, values in data["modules"].items():
        if module not in PROFILE_MODULES:
            errors.append(f"unknown module {module!r} (expected one of {', '.join(PROFILE_MODULES)})")
        elif not isinstance(values, dict) or not values:
            errors.append(f"{module} needs a non-empty object of constants")
        else:
            for name in values:
                if name not in _EDITABLE[module]:
                    errors.append(f"{module}.{name} is not a fork-editable constant")
    return errors


def load_profile(name: str, profiles_dir: "Path | None" = None) -> dict:
    """The profile asset ``<name>.json`` in ``profiles_dir`` (default:
    ``tests/fixtures/profiles``), validated."""
    if not isinstance(name, str) or not _PROFILE_NAME_RE.match(name):
        raise ProfileInvalid(f"a profile name is lower-case letters, digits and '-': {name!r}")
    directory = PROFILES_DIR if profiles_dir is None else Path(profiles_dir)
    path = directory / f"{name}.json"
    if not path.is_file():
        known = ", ".join(profile_names(directory)) or "none"
        raise ProfileInvalid(f"no profile asset named {name!r} (known: {known})")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ProfileInvalid(f"profile {name!r} is not valid JSON: {exc}") from exc
    errors = _profile_errors(data, directory)
    if errors:
        raise ProfileInvalid(f"profile {name!r}: " + "; ".join(errors))
    return data


def shipped_default_profile() -> dict:
    """The frozen shipped defaults as a profile, for a copy that must be the
    default profile whatever the tree it was copied from."""
    return {"description": "The shipped defaults.", "modules": json.loads(json.dumps(SHIPPED_DEFAULTS))}


def with_vocabulary(profile: dict, **overrides: str) -> dict:
    """A copy of ``profile`` with some vocabulary constants replaced."""
    copied = json.loads(json.dumps(profile))
    copied["modules"].setdefault("vocabulary_profile", {}).update(overrides)
    return copied


def copy_scripts_tree(dest: Path, *, with_support: bool = True) -> Path:
    """Copy the framework's ``scripts`` (without its tests) and ``install``
    under ``dest`` and return the copied scripts directory. ``with_support``
    adds this module, the tests package marker and the fixtures it reads, so
    a fresh interpreter over the copy can use the builders and the marker."""
    dest = Path(dest)
    scripts = dest / "scripts"
    shutil.copytree(
        SCRIPTS_DIR, scripts,
        ignore=shutil.ignore_patterns("tests", "benchmarks", "__pycache__", ".pytest_cache", "*.pyc"),
    )
    shutil.copytree(SCRIPTS_DIR.parent / "install", dest / "install")
    if with_support:
        tests = scripts / "tests"
        tests.mkdir()
        for name in ("__init__.py", "record_layout_support.py", "declaration_support.py",
                     "tool_surface_support.py"):
            shutil.copy2(SCRIPTS_DIR / "tests" / name, tests / name)
        for rel in ("docs_lint", "profiles"):
            shutil.copytree(SCRIPTS_DIR / "tests" / "fixtures" / rel, tests / "fixtures" / rel)
    return scripts


_VALIDATE_DRIVER = r"""
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import importlib
import vocabulary_profile, record_paths
spec = json.loads(sys.argv[2])
out = {"loaded": {}, "layout": [], "declaration": []}
for module, names in spec["names"].items():
    loaded = importlib.import_module(module)
    out["loaded"][module] = {name: getattr(loaded, name) for name in names}
if spec["root"]:
    out["layout"] = record_paths.validate_record_layout(Path(spec["root"]))
if "mcp_tool_extensions" in spec["names"]:
    import mcp_tool_extensions, mcp_tool_roster
if "mcp_tool_extensions" in spec["names"] and mcp_tool_extensions.declared():
    # The roster's validation, as the allowlist renderer and the server apply it.
    out["declaration"] = mcp_tool_extensions.declaration_problems(
        core_tools=set(mcp_tool_roster.TOOL_TIERS) - mcp_tool_roster.RUNNER_TOOLS,
        runner_tools=mcp_tool_roster.RUNNER_TOOLS, core_tiers=mcp_tool_roster.TOOL_TIERS)
if "mcp_tool_extensions" in spec["names"] and hasattr(mcp_tool_extensions, "skill_declaration_problems"):
    # Wave 1zv8c (1zv89): the skill declaration, as the renderer checks it.
    out["declaration"] += mcp_tool_extensions.skill_declaration_problems()
if "mcp_tool_extensions" in spec["names"] and hasattr(mcp_tool_extensions, "journal_declaration_problems"):
    # Wave 1zyb3 (1zxnv): the journal migration declaration, as the upgrade checks it.
    out["declaration"] += mcp_tool_extensions.journal_declaration_problems()
print(json.dumps(out))
"""


def replace_file_in(root: Path, path: Path, data: bytes) -> None:
    """Write ``data`` at ``path`` inside ``root`` without following a symlink.

    The bytes go to a temporary file in the same directory, which then
    replaces the path itself (``os.replace`` renames over a symlink rather
    than writing to its target, on Windows as on POSIX), so a symlinked file
    becomes a regular file here and its target is untouched. A path whose
    directory resolves outside ``root`` (a symlinked directory) is refused
    before anything is created."""
    import tempfile

    root_real = Path(os.path.realpath(root))
    parent_real = Path(os.path.realpath(path.parent))
    if parent_real != root_real and root_real not in parent_real.parents:
        raise ProfileInvalid(f"{path}: its directory resolves outside {root} (to {parent_real})")
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = 0o644
    if path.is_file() and not path.is_symlink():
        mode = os.stat(path).st_mode & 0o777
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def apply_profile(scripts_dir: Path, profile: dict, *, modules: "tuple[str, ...] | None" = None,
                  repo_root: "Path | None" = None, python: "str | None" = None,
                  profiles_dir: "Path | None" = None) -> "dict[str, dict[str, Any]]":
    """Edit ``profile``'s constants into the COPIED ``scripts_dir`` the way a
    fork does at merge time, then import the modules in a fresh interpreter
    to validate them (a tool declaration is also checked as the roster
    checks it). Returns every editable constant as loaded there, per module.

    Each constant's assignment must match exactly once. ``modules`` limits
    the edit to some of the profile's modules (a control tree that differs in
    one module only). With ``repo_root`` the layout is also validated against
    that repository. The asset's ``module_files`` (wave 1zyb3) are copied from
    ``profiles_dir`` (default: the tests' own) into the copied scripts
    directory as ``<module>.py`` when the declaration module is edited. Never
    applied to the canonical scripts tree."""
    scripts_dir = Path(scripts_dir)
    try:
        if os.path.samefile(scripts_dir, SCRIPTS_DIR):
            raise ProfileInvalid("apply_profile edits a copied tree, never the canonical scripts directory")
    except OSError:
        pass
    errors = _profile_errors(profile, profiles_dir)
    if errors:
        raise ProfileInvalid("; ".join(errors))
    selected = tuple(m for m in PROFILE_MODULES if m in profile["modules"] and (modules is None or m in modules))
    for module in selected:
        path = scripts_dir / f"{module}.py"
        text = path.read_bytes().decode("utf-8")
        for name, value in profile["modules"][module].items():
            # The value ends before the line ending, which is kept (``\r\n`` included).
            pattern = re.compile(rf"^({re.escape(name)}(?:[ \t]*:[^=\r\n]*)?[ \t]*=[ \t]*)[^\r\n]*(?=\r?$)",
                                 re.MULTILINE)
            if isinstance(_EDITABLE[module][name], tuple):
                value = tuple(value)  # JSON has no tuples; the module's type is kept
            text, count = pattern.subn(lambda m, v=value: m.group(1) + repr(v), text)
            if count != 1:
                raise ProfileInvalid(f"{module}.{name}: {count} assignments matched in {path}, exactly one expected")
        replace_file_in(repo_root if repo_root is not None else scripts_dir, path, text.encode("utf-8"))
    if "mcp_tool_extensions" in selected:
        source_dir = PROFILES_DIR if profiles_dir is None else Path(profiles_dir)
        for module, rel in (profile.get("module_files") or {}).items():
            replace_file_in(repo_root if repo_root is not None else scripts_dir,
                            scripts_dir / f"{module}.py", (source_dir / rel).read_bytes())
    spec = {
        # The declaration module is imported (and checked) only when the
        # profile edits it, so a tree without it still takes a record profile.
        "names": {m: sorted(_EDITABLE[m]) for m in PROFILE_MODULES
                  if m in SHIPPED_DEFAULTS or m in selected},
        "root": str(repo_root) if repo_root is not None else "",
    }
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [python or sys.executable, "-B", "-c", _VALIDATE_DRIVER, str(scripts_dir), json.dumps(spec)],
        cwd=str(scripts_dir), env=env, capture_output=True, text=True, encoding="utf-8",
        errors="replace", check=False, timeout=120,
    )
    if result.returncode != 0:
        raise ProfileInvalid(f"the edited modules do not import: {result.stderr.strip()[-2000:]}")
    out = json.loads(result.stdout.strip().splitlines()[-1])
    for module in selected:
        for name, value in profile["modules"][module].items():
            if out["loaded"][module][name] != value:
                raise ProfileInvalid(f"{module}.{name} loads as {out['loaded'][module][name]!r}, not {value!r}")
    if out["layout"]:
        raise ProfileInvalid("; ".join(out["layout"]))
    if out["declaration"]:
        raise ProfileInvalid("invalid tool declaration: " + "; ".join(out["declaration"]))
    return out["loaded"]


# --- Builders ---------------------------------------------------------------

def _loaded_constants(module_name: str) -> "dict[str, Any]":
    module = __import__(module_name)
    return {name: getattr(module, name) for name in SHIPPED_DEFAULTS[module_name]}


def _join(root: Path, rel: str) -> Path:
    path = Path(root)
    for part in rel.replace("\\", "/").split("/"):
        if part and part != ".":
            path = path / part
    return path


def _record_tail() -> str:
    """The fixed sections after the member list (watchpoints and the two
    projected review regions), taken from the docs-lint fixture's record so
    the builders follow its projection format."""
    text = (DOCS_LINT_FIXTURE / "docs" / "waves" / "change-2026-03" / "wave.md").read_text(encoding="utf-8")
    tail = text[text.index("## Journal Watchpoints"):]
    return tail.replace("## Journal Watchpoints", "## Watchpoints", 1)


class _Vocabulary:
    def __init__(self, fields: "dict[str, str]") -> None:
        for name in _SHIPPED_VOCABULARY:
            setattr(self, name, fields[name])
        self.fields = {name: fields[name] for name in _SHIPPED_VOCABULARY}


class RecordTreeBuilder:
    """Writes records under ``root`` the way a profile expects: the waves
    root and its required README, container records with the profile's
    filename and markers, member blocks, change documents, plans, and the
    archive root's records in the archive profile's vocabulary.

    ``vocabulary`` and ``layout`` are the constants of ``vocabulary_profile``
    and ``record_paths`` (any subset, over the shipped defaults); left out,
    they are read from the loaded modules, so under a profile run the
    builders follow the profile."""

    def __init__(self, root: Path, *, vocabulary: "dict[str, Any] | None" = None,
                 layout: "dict[str, Any] | None" = None) -> None:
        self.root = Path(root)
        self._from_loaded = vocabulary is None
        vocab = (_loaded_constants("vocabulary_profile") if vocabulary is None
                 else {**SHIPPED_DEFAULTS["vocabulary_profile"], **vocabulary})
        self.layout = (_loaded_constants("record_paths") if layout is None
                       else {**SHIPPED_DEFAULTS["record_paths"], **layout})
        self.live = _Vocabulary(vocab)
        archived = vocab.get("ARCHIVE_PROFILE")
        self.archived = _Vocabulary(archived) if archived else self.live

    @property
    def waves_dir(self) -> Path:
        return _join(self.root, self.layout["WAVES_ROOT"])

    @property
    def plans_dir(self) -> Path:
        return _join(self.root, self.layout["PLANS_ROOT"])

    @property
    def archive_dir(self) -> "Path | None":
        archive = self.layout["ARCHIVE_ROOT"]
        return _join(self.root, archive) if archive else None

    def localize(self, text: str, vocab: "_Vocabulary | None" = None) -> str:
        """``vocabulary_profile.localize_template`` applied to ``text`` (written
        with the shipped labels) for ``vocab`` (default: the live profile)."""
        import vocabulary_profile

        vocab = vocab or self.live
        with contextlib.ExitStack() as stack:
            if not (self._from_loaded and vocab is self.live):
                for name, value in vocab.fields.items():
                    stack.enter_context(mock.patch.object(vocabulary_profile, name, value))
            return vocabulary_profile.localize_template(text)

    def waves_readme(self) -> Path:
        """The waves root's required ``README.md`` (written once; an existing
        regular file is kept). It is written with :func:`replace_file_in`, so
        a symlinked README is replaced rather than followed and a waves root
        that resolves outside ``root`` is refused."""
        path = self.waves_dir / "README.md"
        if not (path.is_file() and not path.is_symlink()):
            replace_file_in(self.root, path, (
                f"# {self.live.CONTAINER_NAME_PLURAL}\n\nOwner: Engineering\nStatus: generated\n"
                f"Last verified: {_FIXTURE_DATE}\n\n{self.live.CONTAINER_NAME} records live here.\n"
            ).encode("utf-8"))
        return path

    @staticmethod
    def member_block(vocab: _Vocabulary, change_id: str, status: str, *, previous: "str | None" = None,
                     depends_on: "str | None" = None) -> str:
        lines = [f"{vocab.MEMBER_ID_LABEL}: `{change_id}`"]
        if previous:
            lines.append(f"Previous {vocab.MEMBER_STATUS_LABEL}: `{previous}`")
        lines.append(f"{vocab.MEMBER_STATUS_LABEL}: `{status}`")
        if depends_on:
            lines.append(f"Depends On: `{depends_on}`")
        return "\n".join(lines)

    def container_text(self, wave_id: str, members: "list[tuple]", *, title: str, status: str,
                       vocab: _Vocabulary) -> str:
        blocks = "\n\n".join(
            self.member_block(vocab, m[0], m[1], previous="planned", depends_on=m[2] if len(m) > 2 else None)
            for m in members
        )
        return (
            f"{vocab.RECORD_TITLE}\n\nOwner: Engineering\nStatus: {status}\nLast verified: {_FIXTURE_DATE}\n"
            # producer-fixture: the builders write lint-clean records, which declare their evidence source
            f"Title: {title}\nreview-evidence-source: events.jsonl\n\n{vocab.ID_KEY}: `{wave_id}`\n\n"
            f"## Objective\n\nFixture {vocab.CONTAINER_NAME} written by the profile-aware builders.\n\n"
            f"{vocab.SUMMARY_HEADING}\n\nFixture {vocab.CONTAINER_NAME}.\n\n"
            f"{vocab.MEMBER_HEADING}\n\n{blocks}\n\n{_record_tail()}"
        )

    def change_doc_text(self, change_id: str, *, title: str, status: str, wave: str,
                        vocab: _Vocabulary) -> str:
        done = status in ("complete", "completed")
        text = (
            f"# {title}\n\nChange ID: `{change_id}`\nChange Status: `{status}`\nOwner: Engineering\n"
            f"Status: active\nLast verified: {_FIXTURE_DATE}\nWave: {wave}\n\n"
            f"## Rationale\n\nFixture {vocab.ITEM_NAME} written by the profile-aware builders.\n\n"
            f"## Acceptance Criteria\n\n- [{'x' if done else ' '}] AC-1: Fixture criterion.\n\n"
            "## AC Priority\n\n| AC | Priority |\n|----|----------|\n| AC-1 | required |\n"
        )
        return self.localize(text, vocab)

    def container(self, folder: str, wave_id: str, *, members: "list[tuple]" = (), title: str = "Fixture",
                  status: str = "active", group: str = "", archive: bool = False) -> Path:
        """A container folder with its record, an empty ``events.jsonl`` and a
        change document per member; ``members`` are ``(change_id, status)``
        or ``(change_id, status, depends_on)``. ``group`` nests the folder one
        level down (the layout must be ``NESTED``); ``archive`` writes under
        the archive root in the archive profile's vocabulary."""
        if archive and self.archive_dir is None:
            raise ValueError("the layout has no ARCHIVE_ROOT")
        if group and not self.layout["NESTED"]:
            raise ValueError("a grouping folder needs a NESTED layout")
        vocab = self.archived if archive else self.live
        base = self.archive_dir if archive else self.waves_dir
        if not archive:
            self.waves_readme()
        directory = (base / group / folder) if group else (base / folder)
        directory.mkdir(parents=True, exist_ok=True)
        members = list(members)
        (directory / vocab.RECORD_FILENAME).write_text(
            self.container_text(wave_id, members, title=title, status=status, vocab=vocab), encoding="utf-8")
        (directory / "events.jsonl").write_text("", encoding="utf-8")
        for member in members:
            self.change_doc(directory, member[0], status=member[1], archive=archive)
        return directory

    def change_doc(self, directory: Path, change_id: str, *, status: str = "planned", title: str = "Fixture Change",
                   archive: bool = False) -> Path:
        vocab = self.archived if archive else self.live
        path = Path(directory) / f"{change_id}.md"
        path.write_text(
            self.change_doc_text(change_id, title=title, status=status, wave=Path(directory).name, vocab=vocab),
            encoding="utf-8",
        )
        return path

    def plan(self, change_id: str, *, title: str = "Fixture Plan") -> Path:
        """A planned change document in the plans root (``Wave: TBD``)."""
        self.plans_dir.mkdir(parents=True, exist_ok=True)
        path = self.plans_dir / f"{change_id}.md"
        path.write_text(
            self.change_doc_text(change_id, title=title, status="planned", wave="TBD", vocab=self.live),
            encoding="utf-8",
        )
        return path


def localized_docs_lint_fixture(dest: Path, *, vocabulary: "dict[str, Any] | None" = None,
                                layout: "dict[str, Any] | None" = None) -> Path:
    """A copy of the docs-lint fixture tree at ``dest`` in a profile's
    vocabulary and layout (default: the loaded modules): its records move to
    the configured waves root, each record file takes the profile's name, and
    the shipped markers and labels become the profile's."""
    dest = Path(dest)
    shutil.copytree(DOCS_LINT_FIXTURE, dest)
    builder = RecordTreeBuilder(dest, vocabulary=vocabulary, layout=layout)
    shipped = _Vocabulary(_SHIPPED_VOCABULARY)
    source, target = dest / "docs" / "waves", builder.waves_dir
    if source != target:
        staging = dest / "docs" / ".localizing-waves"
        source.rename(staging)
        target.parent.mkdir(parents=True, exist_ok=True)
        staging.rename(target)
    live = builder.live
    for path in sorted(target.rglob("*.md")):
        if path.name == "README.md":
            continue
        path.write_text(localize_record_text(path.read_text(encoding="utf-8"), vocabulary=live.fields),
                        encoding="utf-8")
        if path.name == shipped.RECORD_FILENAME and live.RECORD_FILENAME != shipped.RECORD_FILENAME:
            path.rename(path.with_name(live.RECORD_FILENAME))
    if live.fields != shipped.fields:
        # The fixture's README names the shipped container; write the profile's.
        (target / "README.md").unlink()
    manifest = dest / "docs" / "prompts" / "prompt-surface-manifest.json"
    if manifest.is_file():
        waves_rel = "/".join(builder.waves_dir.relative_to(dest).parts)
        text = manifest.read_text(encoding="utf-8").replace('"docs/waves/"', json.dumps(waves_rel + "/"))
        manifest.write_text(text, encoding="utf-8")
    builder.waves_readme()
    return dest


def localize_record_text(text: str, *, vocabulary: "dict[str, Any] | None" = None) -> str:
    """Record or change-document ``text`` written in the shipped vocabulary,
    rewritten into ``vocabulary`` (default: the loaded ``vocabulary_profile``):
    the id key, record title, summary and member headings, member id and
    status labels (``Previous`` status lines included), and line-leading
    back-references (``Wave:``). The identity under the shipped profile."""
    live = _Vocabulary({**_SHIPPED_VOCABULARY, **(vocabulary if vocabulary is not None
                                                  else _loaded_constants("vocabulary_profile"))})
    shipped = _Vocabulary(_SHIPPED_VOCABULARY)
    for old, new in (
        (f"{shipped.ID_KEY}:", f"{live.ID_KEY}:"),
        (shipped.RECORD_TITLE, live.RECORD_TITLE),
        (shipped.SUMMARY_HEADING, live.SUMMARY_HEADING),
        (shipped.MEMBER_HEADING, live.MEMBER_HEADING),
        (shipped.MEMBER_ID_LABEL, live.MEMBER_ID_LABEL),
        (shipped.MEMBER_STATUS_LABEL, live.MEMBER_STATUS_LABEL),
    ):
        text = text.replace(old, new)
    backref = re.compile(rf"(?m)^{re.escape(shipped.BACKREF_LABEL)}:")
    return backref.sub(lambda _m: live.BACKREF_LABEL + ":", text)


def waves_dir(root: Path) -> Path:
    """The configured waves root under ``root`` (the loaded ``record_paths``)."""
    import record_paths

    return _join(Path(root), record_paths.WAVES_ROOT)


def waves_rel(*parts: str) -> str:
    """A repo-relative POSIX path under the configured waves root."""
    import record_paths

    base = "/".join(p for p in record_paths.WAVES_ROOT.replace("\\", "/").split("/") if p and p != ".")
    return "/".join([base, *parts])


# --- Expected profile (change 1zima) -----------------------------------------

# The run mode's profile name. ``run_tests.py --profile NAME`` sets it in the
# copy's runner environment; read only by :func:`run_mode_profile_name`.
TEST_PROFILE_ENV = "WAVEFOUNDRY_TEST_PROFILE"


def run_mode_profile_name(environ: "Any | None" = None) -> "str | None":
    """The profile named by ``WAVEFOUNDRY_TEST_PROFILE`` in ``environ``
    (default: ``os.environ``), or ``None`` when it is not set. The one reader
    of the variable: the expected-profile resolver and the runner's refusal of
    a receipt-writing run both ask here."""
    return (os.environ if environ is None else environ).get(TEST_PROFILE_ENV)


@dataclasses.dataclass(frozen=True)
class ProfileLayer:
    """One layer of the expected profile: its name, where it came from
    (``shipped``, ``active asset`` or ``run mode``) and the constants it sets
    per module (empty for the shipped defaults)."""

    name: str
    kind: str
    origin: str
    modules: "dict[str, dict[str, Any]]"

    def describe(self) -> str:
        if self.kind == "shipped":
            return "the shipped defaults"
        return f"{self.name!r} from {self.origin}"


@dataclasses.dataclass(frozen=True)
class ExpectedProfile:
    """The profile the loaded constants must be: the base layer (the active
    asset, else the shipped defaults) and the optional run-mode layer over it,
    overlaid constant by constant the way :func:`apply_profile` edits a copy."""

    base: ProfileLayer
    run_mode: "ProfileLayer | None" = None

    @property
    def layers(self) -> "tuple[ProfileLayer, ...]":
        return (self.base,) if self.run_mode is None else (self.base, self.run_mode)

    @property
    def source(self) -> str:
        """Where the expected profile comes from: ``run mode``, ``active
        asset`` or ``shipped`` (the top layer's kind)."""
        return self.layers[-1].kind

    def describe(self) -> str:
        return ", then ".join(layer.describe() for layer in self.layers)

    def _overlay(self, module: str, shipped: "dict[str, Any]") -> "dict[str, Any]":
        values = dict(shipped)
        for layer in self.layers:
            values.update(layer.modules.get(module, {}))
        return values

    def constants(self) -> "dict[str, dict[str, Any]]":
        """The expected record constants: ``SHIPPED_DEFAULTS`` overlaid with each layer."""
        return {module: self._overlay(module, shipped) for module, shipped in SHIPPED_DEFAULTS.items()}

    def declaration(self) -> "dict[str, Any]":
        """The expected tool declaration: ``SHIPPED_DECLARATION`` overlaid with each layer."""
        return self._overlay("mcp_tool_extensions", SHIPPED_DECLARATION)

    def mismatch_message(self, subject: str, differences: "list[str]") -> str:
        return (f"the loaded {subject} are not the expected profile ({self.describe()}): "
                + "; ".join(differences)
                + f". A distribution marks its own asset \"active\": true; a run mode sets {TEST_PROFILE_ENV}.")


def expected_profile(environ: "Any | None" = None, profiles_dir: "Path | None" = None) -> ExpectedProfile:
    """Resolve the expected profile from ``profiles_dir`` (default:
    ``PROFILES_DIR``) and ``environ`` (default: ``os.environ``).

    The base is the single asset marked ``"active": true``, else the shipped
    defaults; when ``WAVEFOUNDRY_TEST_PROFILE`` names a profile, that asset is
    the run-mode layer over it. Raises :class:`ProfileInvalid`, naming every
    layer and its source, when more than one asset is active, when the
    variable names no usable asset, or when an asset is invalid. Never falls
    back to another profile."""
    directory = PROFILES_DIR if profiles_dir is None else Path(profiles_dir)
    name = run_mode_profile_name(environ)
    run_mode = "" if name is None else f"; run-mode layer: {name!r} from {TEST_PROFILE_ENV}"
    try:
        active = [(asset, data) for asset in profile_names(directory)
                  for data in (load_profile(asset, directory),) if data.get("active") is True]
    except ProfileInvalid as exc:
        raise ProfileInvalid(f"{exc}{run_mode}") from exc
    if len(active) > 1:
        raise ProfileInvalid(
            "more than one profile asset is marked active in "
            f"{directory}: {', '.join(f'{asset}.json' for asset, _ in active)}; at most one may be "
            f"(a distribution marks its own){run_mode}")
    base = (ProfileLayer(active[0][0], "active asset", f"the active asset {active[0][0]}.json",
                         active[0][1]["modules"])
            if active else ProfileLayer("shipped", "shipped", "the shipped defaults", {}))
    if name is None:
        return ExpectedProfile(base)
    try:
        data = load_profile(name, directory)
    except ProfileInvalid as exc:
        raise ProfileInvalid(
            f"{TEST_PROFILE_ENV}={name!r} names no usable profile asset ({exc}); "
            f"base layer: {base.describe()}") from exc
    return ExpectedProfile(base, ProfileLayer(name, "run mode", TEST_PROFILE_ENV, data["modules"]))


def _json_form(value: Any) -> Any:
    """JSON form (tuples as lists), as a profile asset writes a constant."""
    return json.loads(json.dumps(value))


def expected_profile_mismatch(expected: ExpectedProfile) -> "str | None":
    """``None`` when every loaded copy of ``vocabulary_profile`` and
    ``record_paths`` equals ``expected``'s record constants exactly, compared
    in JSON form (tuples as lists) as ``declaration_profile_mismatch`` does, so
    a loaded ``("decision",)`` matches an asset's ``["decision"]`` (wave
    1zimf); else a message naming each layer, its source and each differing
    constant."""
    want = expected.constants()
    differences: list[str] = []
    for module_name, values in want.items():
        for module in _loaded_modules(module_name):
            loaded = _constants_of(module, module_name)
            for name, value in values.items():
                if loaded[name] is _MISSING or _json_form(loaded[name]) != _json_form(value):
                    got = "missing" if loaded[name] is _MISSING else repr(loaded[name])
                    differences.append(f"{module_name}.{name} is {got}, expected {value!r}")
    if not differences:
        return None
    return expected.mismatch_message("record constants", list(dict.fromkeys(differences)))


def write_waves_readme(root: Path, *, vocabulary: "dict[str, Any] | None" = None,
                       layout: "dict[str, Any] | None" = None) -> Path:
    """The configured waves root's required README under ``root``."""
    return RecordTreeBuilder(root, vocabulary=vocabulary, layout=layout).waves_readme()


# --- Default-profile-only marker ---------------------------------------------

_MISSING = object()


def _loaded_modules(name: str) -> list[Any]:
    found = [mod for key, mod in list(sys.modules.items())
             if mod is not None and (key == name or key.endswith("." + name))]
    if not found:
        found.append(__import__(name))
    return list(dict.fromkeys(found))


def _constants_of(module: Any, module_name: str) -> "dict[str, Any]":
    return {name: getattr(module, name, _MISSING) for name in SHIPPED_DEFAULTS[module_name]}


def profile_differences() -> list[str]:
    """``module.CONSTANT`` names whose loaded value differs from the frozen
    shipped default, across every loaded copy of each module; empty under
    the shipped profile."""
    differ: set[str] = set()
    for module_name, defaults in SHIPPED_DEFAULTS.items():
        for module in _loaded_modules(module_name):
            for name, value in defaults.items():
                if getattr(module, name, _MISSING) != value:
                    differ.add(f"{module_name}.{name}")
    return sorted(differ)


def _skip_unless_shipped_profile(reason: str) -> None:
    differ = profile_differences()
    if differ:
        raise unittest.SkipTest(
            f"default-profile-only: {reason} (loaded {', '.join(differ)} differ from the shipped defaults)")


def default_profile_only(reason: str):
    """Mark a test (method or ``TestCase`` class) whose subject is the shipped
    default profile: golden outputs, stock-surface pins, censuses of this
    repository's own documents, the default-path constants. It is skipped,
    with ``reason``, when the loaded constants differ from the frozen shipped
    defaults; decided when the test runs, before ``setUp`` (or ``setUpClass``
    for a class). ``reason`` is one line."""
    if not isinstance(reason, str) or not reason.strip() or "\n" in reason:
        raise ValueError("default_profile_only needs a one-line reason")

    def decorate(target):
        if isinstance(target, type):
            original = target.__dict__.get("setUpClass")

            def setUpClass(cls):  # noqa: N802 (unittest name)
                _skip_unless_shipped_profile(reason)
                if original is not None:
                    original.__func__(cls)
                else:
                    super(target, cls).setUpClass()

            target.setUpClass = classmethod(setUpClass)
            target.__default_profile_only__ = reason
            return target

        return _MarkedTest(target, reason)

    return decorate


class _MarkedTest:
    """A marked test method. Placed in a ``TestCase`` body it replaces itself
    with a skipping wrapper and wraps the class's ``setUp``, so the skip is
    decided before ``setUp`` runs; called directly it skips the same way."""

    def __init__(self, func, reason: str) -> None:
        functools.update_wrapper(self, func)
        self.func = func
        self.__default_profile_only__ = reason

    def __call__(self, *args, **kwargs):
        _skip_unless_shipped_profile(self.__default_profile_only__)
        return self.func(*args, **kwargs)

    def __set_name__(self, owner, name) -> None:
        func, reason = self.func, self.__default_profile_only__

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            _skip_unless_shipped_profile(reason)
            return func(*args, **kwargs)

        wrapper.__default_profile_only__ = reason
        setattr(owner, name, wrapper)
        if "_default_profile_only_setup" not in owner.__dict__:
            original = owner.setUp

            def setUp(self, *args, **kwargs):  # noqa: N802 (unittest name)
                method = getattr(self, self._testMethodName, None)
                marked = getattr(method, "__default_profile_only__", None)
                if marked:
                    _skip_unless_shipped_profile(marked)
                return original(self, *args, **kwargs)

            owner.setUp = setUp
            owner._default_profile_only_setup = True
