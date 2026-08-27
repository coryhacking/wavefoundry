#!/usr/bin/env python3
"""Shard preservation verification for wave 1tmtx / 1tm6d (AC-3, Requirements 6-7).

Checks, against the frozen Requirement 1 inventory (freeze.json):
  1. IDENTITY — the union of (class, test_method) identities across the three
     shard files exactly equals the frozen test_server_tools.py identity set;
     no duplicates across shards; every shard nonempty.
  2. FINGERPRINTS — every shard class's normalized ast.dump fingerprint equals
     its frozen fingerprint. Exception map (Requirement 7, separately
     reviewed): FrameworkWideSubprocessIsolationGuard, whose six scan seams
     were rebound to server_tools_support; the map entry is proven by
     comparing each support function's AST against the HEAD original method
     transformed by the documented rename map.
  3. CENSUS — no test_*.py imports or importlib-executes another test_*.py;
     the self-referential reader-census class stays in the file whose
     basename its filter names; the support module defines no
     discovery-shaped names.
  4. MUTANTS — five named mutants applied to scratch-tree copies must each be
     caught by checks 1-2 (delete-class, delete-plus-padding,
     assertion-to-pass, duplicate-class, new-skip).

Run: python3 verify_shards.py   → writes verify_shards.json, exit 0 iff all pass.
"""

import ast
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parent
REPO = EVIDENCE.parents[3]
TESTS = REPO / ".wavefoundry" / "framework" / "scripts" / "tests"
FREEZE = json.loads((EVIDENCE / "freeze.json").read_text(encoding="utf-8"))
MANIFEST = json.loads((EVIDENCE / "shard_manifest.json").read_text(encoding="utf-8"))
GUARD = "FrameworkWideSubprocessIsolationGuard"
SHARDS = list(MANIFEST["shards"])
SOURCE_REF = "HEAD:.wavefoundry/framework/scripts/tests/test_server_tools.py"

sys.path.insert(0, str(EVIDENCE))
from shard_split import MEMBER_TRANSFORMS  # noqa: E402 — single source of the rename map


def fingerprint(node) -> str:
    return hashlib.sha256(ast.dump(node, include_attributes=False).encode("utf-8")).hexdigest()


def shard_class_nodes(path: Path) -> list[ast.ClassDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [n for n in tree.body if isinstance(n, ast.ClassDef)]


def shard_classes(path: Path) -> dict[str, ast.ClassDef]:
    return {n.name: n for n in shard_class_nodes(path)}


def identities_of(node: ast.ClassDef) -> set[tuple[str, str]]:
    return {(node.name, m.name) for m in node.body
            if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and m.name.startswith("test_")}


def check_identity_and_fingerprints(files: dict[str, Path]) -> list[str]:
    """Checks 1-2 against a set of shard files (real tree or mutant copies)."""
    violations: list[str] = []
    frozen_ids = {(c, m) for f, c, m in FREEZE["static_identities"] if f == "test_server_tools.py"}
    frozen_fps = {k.split("::", 1)[1]: v for k, v in FREEZE["class_fingerprints"].items()
                  if k.startswith("test_server_tools.py::")}

    seen_ids: set[tuple[str, str]] = set()
    seen_classes: dict[str, str] = {}
    for shard, path in files.items():
        nodes = shard_class_nodes(path)
        if not nodes:
            violations.append(f"{shard}: empty shard")
        for node in nodes:
            name = node.name
            if name in seen_classes:
                violations.append(f"duplicate class {name} in {shard} and {seen_classes[name]}")
            seen_classes[name] = shard
            ids = identities_of(node)
            dup = ids & seen_ids
            if dup:
                violations.append(f"duplicate identities across shards: {sorted(dup)[:3]}")
            seen_ids |= ids
            if name == GUARD:
                continue  # exception map — proven separately in check_guard_exception
            frozen = frozen_fps.get(name)
            if frozen is None:
                violations.append(f"{shard}: class {name} not in frozen inventory")
            elif fingerprint(node) != frozen:
                violations.append(f"{shard}: fingerprint mismatch for {name}")
    missing = frozen_ids - seen_ids
    extra = seen_ids - frozen_ids
    if missing:
        violations.append(f"missing identities: {sorted(missing)[:5]} (+{max(0, len(missing) - 5)} more)")
    if extra:
        violations.append(f"extra identities: {sorted(extra)[:5]}")
    return violations


def check_guard_exception() -> list[str]:
    """Prove the Requirement 7 exception-map entry mechanically.

    Each support scan function's normalized AST must equal the HEAD original
    Guard method transformed by the documented rename map; and the on-disk
    Guard must rebind exactly those six names via staticmethod with no other
    member difference from HEAD (tests and retained members byte-frozen).
    """
    violations: list[str] = []
    head_src = subprocess.run(["git", "-C", str(REPO), "show", SOURCE_REF],
                              capture_output=True, text=True, check=True).stdout
    head_lines = head_src.splitlines(keepends=True)
    head_guard = next(n for n in ast.parse(head_src).body
                      if isinstance(n, ast.ClassDef) and n.name == GUARD)
    support_tree = ast.parse((TESTS / "server_tools_support.py").read_text(encoding="utf-8"))
    support_fns = {n.name: n for n in support_tree.body if isinstance(n, ast.FunctionDef)}

    import textwrap
    for member in head_guard.body:
        if not isinstance(member, ast.FunctionDef) or member.name not in MEMBER_TRANSFORMS:
            continue
        start = min([member.lineno] + [d.lineno for d in member.decorator_list])
        text = "".join(head_lines[start - 1:member.end_lineno])
        text = "".join(ln for ln in text.splitlines(keepends=True) if not ln.strip().startswith("@"))
        text = textwrap.dedent(text)
        for old, new in MEMBER_TRANSFORMS[member.name]:
            text = text.replace(old, new)
        expected = ast.parse(text).body[0]
        actual = support_fns.get(member.name)
        if actual is None:
            violations.append(f"support missing {member.name}")
        elif ast.dump(expected, include_attributes=False) != ast.dump(actual, include_attributes=False):
            violations.append(f"support {member.name} AST differs from transformed HEAD original")

    disk_guard = shard_classes(TESTS / "test_server_tools.py").get(GUARD)
    if disk_guard is None:
        return violations + ["retained shard lacks the Guard class"]
    rebinds = {m.targets[0].id for m in disk_guard.body
               if isinstance(m, ast.Assign) and isinstance(m.value, ast.Call)
               and getattr(m.value.func, "id", "") == "staticmethod"}
    if rebinds != set(MEMBER_TRANSFORMS):
        violations.append(f"guard rebinds {sorted(rebinds)} != expected {sorted(MEMBER_TRANSFORMS)}")
    # every OTHER member of the disk Guard must be fingerprint-identical to HEAD
    head_members = {m.name: m for m in head_guard.body if isinstance(m, ast.FunctionDef)}
    disk_members = {m.name: m for m in disk_guard.body if isinstance(m, ast.FunctionDef)}
    for name, node in disk_members.items():
        if name in MEMBER_TRANSFORMS:
            violations.append(f"guard still defines moved member {name} inline")
        elif name not in head_members:
            violations.append(f"guard gained member {name}")
        elif ast.dump(node, include_attributes=False) != ast.dump(head_members[name], include_attributes=False):
            violations.append(f"guard member {name} differs from HEAD")
    missing_members = set(head_members) - set(disk_members) - set(MEMBER_TRANSFORMS)
    if missing_members:
        violations.append(f"guard lost members: {sorted(missing_members)}")
    ids_head = identities_of(head_guard)
    ids_disk = identities_of(disk_guard)
    if ids_head != ids_disk:
        violations.append(f"guard test identities changed: -{ids_head - ids_disk} +{ids_disk - ids_head}")
    return violations


# Pre-existing cross-test imports OUTSIDE the server-tools family and outside
# 1tm6d's licensed scope (none of these files are in this wave's In-scope
# list). Both predate the shard work — disclosed here rather than silently
# repaired; follow-up candidates recorded in the change doc. The second entry
# was surfaced by the delivery architecture lane after widening the predicate
# to the package-qualified `from tests.test_*` form. A SELF-import (a module
# importing itself for multiprocessing spawn pickling) is not "another"
# test module and is exempt from the predicate.
PREEXISTING_CROSS_TEST_IMPORTS = {
    ("test_render_agent_surfaces.py", "test_upgrade_wavefoundry"),
    ("test_techdocs_audit_lib.py", "tests.test_render_agent_surfaces"),
}


def check_census() -> tuple[list[str], list[str]]:
    violations: list[str] = []
    preexisting: list[str] = []
    for tf in sorted(TESTS.glob("test_*.py")):
        src = tf.read_text(encoding="utf-8")
        tree = ast.parse(src)
        for node in ast.walk(tree):
            imported = []
            if isinstance(node, ast.Import):
                imported = [a.name for a in node.names
                            if a.name.startswith("test_") or a.name.startswith("tests.test_")]
            elif isinstance(node, ast.ImportFrom) and (
                    (node.module or "").startswith("test_")
                    or (node.module or "").startswith("tests.test_")):
                imported = [node.module]
            for mod in imported:
                if mod in (tf.stem, f"tests.{tf.stem}"):
                    continue  # self-import (spawn pickling) — not "another" module
                if (tf.name, mod) in PREEXISTING_CROSS_TEST_IMPORTS:
                    preexisting.append(f"{tf.name}: from-imports {mod} (pre-existing, out of 1tm6d scope)")
                else:
                    violations.append(f"{tf.name}: imports {mod}")
        for m in re.finditer(r"spec_from_file_location\([^)]*\btest_\w+\.py", src):
            violations.append(f"{tf.name}: importlib-executes a test module ({m.group(0)[:60]})")
    # self-referential reader-census filter stays with its host basename
    retained = (TESTS / "test_server_tools.py").read_text(encoding="utf-8")
    if "WaveCurrentMigrationGrepTests" not in retained:
        violations.append("reader-census class left the retained basename")
    if '"test_server_tools.py" not in line' not in retained:
        violations.append("self-referential filter no longer matches its host basename")
    support_tree = ast.parse((TESTS / "server_tools_support.py").read_text(encoding="utf-8"))
    for n in support_tree.body:
        name = getattr(n, "name", None)
        if name and (name.startswith("test_") or name.startswith("Test")):
            violations.append(f"support defines discovery-shaped name {name}")
    return violations, preexisting


MUTANTS = {
    "delete_class": lambda src: _drop_class(src, "GetPromptTests"),
    "delete_plus_padding": lambda src: _drop_class(src, "GetPromptTests")
    + "\n" * (len(_class_text(src, "GetPromptTests").splitlines())),
    "assertion_to_pass": lambda src: src.replace(
        _first_assert_line(src), _first_assert_line(src).split("self.assert")[0] + "pass\n", 1),
    "duplicate_class": lambda src: src + "\n\n" + _class_text(src, "GetPromptTests"),
    "new_skip": lambda src: src.replace(
        "class GetPromptTests(", "@unittest.skip(\"mutant\")\nclass GetPromptTests(", 1),
}


def _class_text(src: str, name: str) -> str:
    tree = ast.parse(src)
    node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == name)
    return "".join(src.splitlines(keepends=True)[node.lineno - 1:node.end_lineno])


def _drop_class(src: str, name: str) -> str:
    return src.replace(_class_text(src, name), "", 1)


def _first_assert_line(src: str) -> str:
    text = _class_text(src, "GetPromptTests")
    for ln in text.splitlines(keepends=True):
        if ln.strip().startswith("self.assert"):
            return ln
    raise AssertionError("no assertion line found in GetPromptTests")


def run_mutants() -> dict[str, bool]:
    """Each mutant must be CAUGHT (nonempty violations). Scratch tree only."""
    host_shard = next(s for s, members in MANIFEST["shards"].items() if "GetPromptTests" in members)
    caught: dict[str, bool] = {}
    with tempfile.TemporaryDirectory() as td:
        scratch = Path(td)
        for shard in SHARDS:
            shutil.copy2(TESTS / shard, scratch / shard)
        for mutant, apply in MUTANTS.items():
            src = (TESTS / host_shard).read_text(encoding="utf-8")
            (scratch / host_shard).write_text(apply(src), encoding="utf-8")
            files = {s: scratch / s for s in SHARDS}
            caught[mutant] = bool(check_identity_and_fingerprints(files))
            (scratch / host_shard).write_text(src, encoding="utf-8")
    return caught


def main() -> int:
    files = {s: TESTS / s for s in SHARDS}
    census_violations, census_preexisting = check_census()
    report = {
        "identity_and_fingerprints": check_identity_and_fingerprints(files),
        "guard_exception_map": check_guard_exception(),
        "census": census_violations,
        "census_preexisting_exclusions": census_preexisting,
        "mutants_caught": run_mutants(),
    }
    ok = (not report["identity_and_fingerprints"] and not report["guard_exception_map"]
          and not report["census"] and all(report["mutants_caught"].values()))
    report["pass"] = ok
    (EVIDENCE / "verify_shards.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
