#!/usr/bin/env python3
"""Mechanical shard split of test_server_tools.py (wave 1tmtx / 1tm6d, Requirements 6-7).

Byte-exact segment relocation driven by shard_manifest.json:
  - server_tools_support.py: the 12 shared fixture helpers + SCRIPTS_ROOT/
    SERVER_PATH + the six subprocess-scan seams extracted from
    FrameworkWideSubprocessIsolationGuard (rename map below; the Guard rebinds
    them via staticmethod so every self./cls. call site works unchanged).
  - test_server_tools.py (retained), test_server_tools_retrieval.py,
    test_server_tools_lifecycle.py: whole classes byte-copied in original
    order, localized helpers/constants co-located with their consumers.

Safety gates (all run BEFORE any file is written):
  1. every top-level node is explicitly assigned (no silent drops),
  2. no shard references a top-level name that landed in a different shard
     (support names excluded — they are imported everywhere),
  3. every relocated class's normalized AST fingerprint equals the frozen
     fingerprint from freeze.json (exception map: the Guard, whose seam
     rebinding is the separately reviewed Requirement 7 entry),
  4. the generated support module parses and defines exactly the expected names.

Run: python3 shard_split.py [--write]   (default is dry-run: report only)
"""

import ast
import hashlib
import json
import sys
import textwrap
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parent
REPO = EVIDENCE.parents[3]
TESTS = REPO / ".wavefoundry" / "framework" / "scripts" / "tests"
# The split is regenerable: always read the pristine pre-split module from git
# HEAD (the working-tree file becomes the retained core shard after --write).
import subprocess as _subprocess  # noqa: E402

SOURCE_REF = "HEAD:.wavefoundry/framework/scripts/tests/test_server_tools.py"

MANIFEST = json.loads((EVIDENCE / "shard_manifest.json").read_text(encoding="utf-8"))
FREEZE = json.loads((EVIDENCE / "freeze.json").read_text(encoding="utf-8"))
GUARD = "FrameworkWideSubprocessIsolationGuard"
SUPPORT_NAME = MANIFEST["support_module"]

SHARD_DOCSTRINGS = {
    "test_server_tools.py": (
        "Server core/infrastructure MCP tool tests (shard 1 of 3, wave 1tmtx).\n\n"
        "Retains the original basename: hosts the framework-wide subprocess\n"
        "isolation guard (scan seams live in server_tools_support) and the\n"
        "reader-census test whose grep filter names this file. Shared fixtures\n"
        "come from server_tools_support; sibling shards are\n"
        "test_server_tools_retrieval.py and test_server_tools_lifecycle.py."
    ),
    "test_server_tools_retrieval.py": (
        "Retrieval/navigation/graph/index MCP tool tests (shard 2 of 3, wave\n"
        "1tmtx), split from test_server_tools.py; shared fixtures come from\n"
        "server_tools_support."
    ),
    "test_server_tools_lifecycle.py": (
        "Wave lifecycle/review/governance MCP tool tests (shard 3 of 3, wave\n"
        "1tmtx), split from test_server_tools.py; shared fixtures come from\n"
        "server_tools_support."
    ),
}

SUPPORT_IMPORT = (
    "import server_tools_support\n"
    "from server_tools_support import (  # noqa: F401 — shared server-test fixtures\n"
    "    SCRIPTS_ROOT,\n    SERVER_PATH,\n    integrity_checks,\n    load_server,\n"
    "    load_thin_runner,\n    _make_repo,\n    _store_read_meta,\n"
    "    _seed_store_state,\n    _write_index_layer,\n    _write_lance_index,\n)\n"
)

GUARD_REBIND = textwrap.indent(textwrap.dedent("""\
    # Wave 1tmtx (1tm6d): the AST scan seams live in server_tools_support so
    # non-test consumers (test_render_platform_surfaces) import pure support
    # callables instead of executing this test module. staticmethod rebinding
    # keeps every existing self./cls. call site working unchanged.
    _subprocess_aliases = staticmethod(server_tools_support._subprocess_aliases)
    _spawn_calls = staticmethod(server_tools_support._spawn_calls)
    _call_kwarg_names = staticmethod(server_tools_support._call_kwarg_names)
    _call_has_devnull_or_input = staticmethod(server_tools_support._call_has_devnull_or_input)
    _call_has_no_window = staticmethod(server_tools_support._call_has_no_window)
    _is_isolated_helper_call = staticmethod(server_tools_support._is_isolated_helper_call)
"""), "    ")

# Rename map applied to the moved Guard members (documented for the
# Requirement 7 exception-map review; everything else is byte-identical).
MEMBER_TRANSFORMS = {
    "_subprocess_aliases": [
        ("FrameworkWideSubprocessIsolationGuard._SPAWN_ATTRS", "SPAWN_ATTRS"),
    ],
    "_spawn_calls": [
        ("def _spawn_calls(cls, tree):", "def _spawn_calls(tree):"),
        ("cls._subprocess_aliases(", "_subprocess_aliases("),
        ("cls._SPAWN_ATTRS", "SPAWN_ATTRS"),
    ],
    "_call_kwarg_names": [],
    "_call_has_devnull_or_input": [],
    "_call_has_no_window": [],
    "_is_isolated_helper_call": [
        ("def _is_isolated_helper_call(cls, node) -> bool:",
         "def _is_isolated_helper_call(node) -> bool:"),
    ],
}


def node_name(node) -> str | None:
    if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
        return node.name
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        return node.targets[0].id
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id
    return None


def span_start(node) -> int:
    decos = getattr(node, "decorator_list", None) or []
    return min([node.lineno] + [d.lineno for d in decos])


def normalized_fingerprint(node) -> str:
    return hashlib.sha256(ast.dump(node, include_attributes=False).encode("utf-8")).hexdigest()


def main() -> int:
    write = "--write" in sys.argv[1:]
    src = _subprocess.run(
        ["git", "-C", str(REPO), "show", SOURCE_REF],
        capture_output=True, text=True, encoding="utf-8", check=True,
    ).stdout
    lines = src.splitlines(keepends=True)
    tree = ast.parse(src)

    # ---- segment the module ------------------------------------------------
    import_end = max(n.end_lineno for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom)))
    header = "".join(lines[:import_end])

    body_nodes = [n for n in tree.body if not isinstance(n, (ast.Import, ast.ImportFrom))]

    class_shard = {}
    for shard, members in MANIFEST["shards"].items():
        for m in members:
            class_shard[m] = shard

    assignments: dict[str, list[str]] = {s: [] for s in MANIFEST["shards"]}
    support_assign_segs: list[str] = []
    support_helper_segs: list[str] = []
    unassigned: list[str] = []
    guard_segment = None

    prev_end = import_end
    for node in body_nodes:
        start = span_start(node)
        seg = "".join(lines[prev_end:node.end_lineno])
        prev_end = node.end_lineno
        name = node_name(node)
        if isinstance(node, ast.If) and "__main__" in ast.dump(node.test):
            # The original module carries a MID-FILE `if __name__ == "__main__"`
            # guard (line 33882) with no EOF block — the latent 1t018 hazard
            # (direct execution would stop before later classes). Dropped here;
            # every generated shard gets a proper EOF main block instead.
            continue
        if name is None:
            unassigned.append(f"line {node.lineno}: {type(node).__name__}")
            continue
        if name in MANIFEST["support_assigns"]:
            support_assign_segs.append(seg)
        elif name in MANIFEST["support_helpers"]:
            support_helper_segs.append(seg)
        elif name in MANIFEST["localized"]:
            assignments[MANIFEST["localized"][name]].append(seg)
        elif name in class_shard:
            if name == GUARD:
                guard_segment = (node, seg, start)
            else:
                assignments[class_shard[name]].append(seg)
        else:
            unassigned.append(f"line {node.lineno}: {type(node).__name__} {name}")
    if unassigned:
        print("GATE 1 FAILED — unassigned top-level nodes:\n  " + "\n  ".join(unassigned))
        return 1
    if guard_segment is None:
        print("GATE 1 FAILED — Guard class not found")
        return 1

    # ---- Guard surgery + support member extraction -------------------------
    guard_node, guard_seg, guard_start = guard_segment
    moved = {m.name: m for m in guard_node.body
             if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
             and m.name in MANIFEST["guard_moved_members"]}
    if set(moved) != set(MANIFEST["guard_moved_members"]):
        print(f"GATE 1 FAILED — guard members missing: {set(MANIFEST['guard_moved_members']) - set(moved)}")
        return 1
    starts = [span_start(m) for m in moved.values()]
    ends = [m.end_lineno for m in moved.values()]
    cut_a, cut_b = min(starts), max(ends)  # 1-indexed inclusive block
    between = [m for m in guard_node.body
               if span_start(m) >= cut_a and m.end_lineno <= cut_b
               and node_name(m) not in MANIFEST["guard_moved_members"]
               and not isinstance(m, ast.Expr)]
    if between:
        print(f"GATE 1 FAILED — non-moved members inside the cut block: {[node_name(m) for m in between]}")
        return 1

    support_fns = []
    for member_name in MANIFEST["guard_moved_members"]:
        m = moved[member_name]
        m_start = span_start(m)
        body_text = "".join(lines[m_start - 1:m.end_lineno])
        # drop decorator lines (@staticmethod/@classmethod), dedent one level
        body_lines = [ln for ln in body_text.splitlines(keepends=True)
                      if not ln.strip().startswith("@")]
        fn_text = textwrap.dedent("".join(body_lines))
        for old, new in MEMBER_TRANSFORMS[member_name]:
            if old not in fn_text:
                print(f"GATE 4 FAILED — transform anchor missing in {member_name}: {old!r}")
                return 1
            fn_text = fn_text.replace(old, new)
        support_fns.append(fn_text)

    # new Guard segment: original bytes with the cut block replaced by rebinding
    seg_offset = guard_start - 1 - (guard_node.end_lineno - len(guard_seg.splitlines()))
    guard_lines = guard_seg.splitlines(keepends=True)
    seg_first_lineno = guard_node.end_lineno - len(guard_lines) + 1
    a_idx = cut_a - seg_first_lineno
    b_idx = cut_b - seg_first_lineno + 1
    new_guard_seg = "".join(guard_lines[:a_idx]) + GUARD_REBIND + "".join(guard_lines[b_idx:])
    assignments["test_server_tools.py"].append(new_guard_seg)
    # keep original in-file order: Guard was appended last, so re-sort segments
    # of the retained shard by their first line number in the ORIGINAL source.
    # (Segments embed no line info, so tag by search — original order equals
    # append order except for the Guard, which we re-insert at position 1.)
    core = assignments["test_server_tools.py"]
    core.insert(1, core.pop())  # Guard follows McpSubprocessHelperTests, its original neighbor

    # ---- build support module ----------------------------------------------
    spawn_attrs_line = 'SPAWN_ATTRS = {"run", "Popen", "call", "check_output", "check_call"}\n'
    support_doc = (
        '"""Shared server-tool test support (wave 1tmtx / 1tm6d).\n\n'
        "Pure fixture helpers and the framework-wide subprocess-scan seams used\n"
        "by the test_server_tools* shards and by test_render_platform_surfaces\n"
        "and test_graph_query. Deliberately NOT unittest-discovered: no TestCase,\n"
        "no test_* names, no module-level mutable/cache/singleton server state —\n"
        "helpers mutate process state only when explicitly called (Requirement 6\n"
        'of 1tm6d).\n"""\n'
    )
    support_src = (
        support_doc + header + "\n" + spawn_attrs_line + "\n"
        + "".join(support_assign_segs) + "".join(support_helper_segs)
        + "\n\n" + "\n\n".join(fn.rstrip("\n") for fn in support_fns) + "\n"
    )
    try:
        support_tree = ast.parse(support_src)
    except SyntaxError as exc:
        print(f"GATE 4 FAILED — support module does not parse: {exc}")
        return 1
    support_defs = {node_name(n) for n in support_tree.body if node_name(n)}
    expected = (set(MANIFEST["support_assigns"]) | set(MANIFEST["support_helpers"])
                | set(MANIFEST["guard_moved_members"]) | {"SPAWN_ATTRS"})
    if not expected <= support_defs:
        print(f"GATE 4 FAILED — support missing: {expected - support_defs}")
        return 1
    if any(n.startswith("test_") or n.startswith("Test") for n in support_defs):
        print("GATE 4 FAILED — support defines discovery-shaped names")
        return 1
    # Support must be self-contained: no reference to any shard-defined
    # top-level name (found the hard way — _append_typed_approval reached
    # WaveLifecycleMutationTests._approval_record before its relocation).
    shard_class_names = set(class_shard) | set(MANIFEST["localized"])
    support_leaks = []
    for n in support_tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            used = {x.id for x in ast.walk(n) if isinstance(x, ast.Name)}
            leaks = used & (shard_class_names - support_defs)
            if leaks:
                support_leaks.append(f"{n.name} -> {sorted(leaks)}")
    if support_leaks:
        print("GATE 4 FAILED — support references shard-defined names:\n  "
              + "\n  ".join(support_leaks))
        return 1

    # ---- assemble shard sources -------------------------------------------
    shard_sources = {}
    for shard, segs in assignments.items():
        doc = SHARD_DOCSTRINGS[shard]
        shard_sources[shard] = (
            f'"""{doc}\n"""\n' + header + SUPPORT_IMPORT
            + "".join(segs)
            + '\n\nif __name__ == "__main__":\n    unittest.main()\n'
        )

    # ---- gate 2: cross-shard name references -------------------------------
    all_top_names = {}
    for shard, segs_src in shard_sources.items():
        t = ast.parse(segs_src)
        for n in t.body:
            nm = node_name(n)
            if nm:
                all_top_names.setdefault(nm, shard)
    problems = []
    for shard, shard_src in shard_sources.items():
        t = ast.parse(shard_src)
        used = {n.id for n in ast.walk(t) if isinstance(n, ast.Name)}
        for nm in used:
            owner = all_top_names.get(nm)
            if owner and owner != shard and nm not in support_defs:
                problems.append(f"{shard} references {nm!r} defined in {owner}")
    if problems:
        print("GATE 2 FAILED — cross-shard references:\n  " + "\n  ".join(sorted(set(problems))))
        return 1

    # ---- gate 3: fingerprints vs freeze ------------------------------------
    frozen = {k.split("::", 1)[1]: v for k, v in FREEZE["class_fingerprints"].items()
              if k.startswith("test_server_tools.py::")}
    mismatches, seen = [], set()
    for shard, shard_src in shard_sources.items():
        for n in ast.parse(shard_src).body:
            if isinstance(n, ast.ClassDef):
                seen.add(n.name)
                if n.name == GUARD:
                    continue  # Requirement 7 exception map: seam rebinding, reviewed
                if normalized_fingerprint(n) != frozen.get(n.name):
                    mismatches.append(f"{shard}: {n.name}")
    missing = set(frozen) - seen
    extra = seen - set(frozen)
    if mismatches or missing or extra:
        print(f"GATE 3 FAILED — fingerprint mismatches={mismatches} missing={sorted(missing)} extra={sorted(extra)}")
        return 1

    counts = {s: sum(1 for n in ast.parse(t).body if isinstance(n, ast.ClassDef))
              for s, t in shard_sources.items()}
    print(f"all gates passed: classes per shard {counts} + support ({len(support_defs)} names); "
          f"guard exception-map entry: seam rebinding with rename map {list(MEMBER_TRANSFORMS)}")
    if not write:
        print("dry-run only — re-run with --write to write files")
        return 0
    (TESTS / SUPPORT_NAME).write_text(support_src, encoding="utf-8")
    for shard, shard_src in shard_sources.items():
        (TESTS / shard).write_text(shard_src, encoding="utf-8")
    print(f"wrote {SUPPORT_NAME} and {len(shard_sources)} shard files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
