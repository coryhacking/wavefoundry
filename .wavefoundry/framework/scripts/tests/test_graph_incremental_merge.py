"""Tests for the incremental graph merge + per-file state store (wave 1p9q2).

Covers:
- ``GraphStateStore`` unit behavior (get/put/delete/iterate, version reset,
  legacy monolithic-state discard, corruption recovery, I/O counters).
- The randomized DIFFERENTIAL HARNESS: for seeded edit sequences over fixture
  corpora, the incrementally-maintained graph must equal a from-scratch
  full-rebuild oracle of the same tree after every step — same node set (full
  node dicts), same edge-key set (source, target, relation, confidence), same
  ``input_fingerprint`` (AC-2).
- Targeted twin-flip faithfulness: demotion when a same-name twin appears in
  an untouched file's candidate set, promotion when one is deleted,
  import-disambiguation rebinds, and rename release+bind (AC-3).
- Version/epoch invalidation + one-time idempotent legacy discard (AC-4).
- Crash consistency via fault injection at each persist window (AC-5).
- Zero-change fast path + O(changed) state-I/O counters (AC-1).
- Fingerprint-gated cluster/betweenness recompute skip (AC-6).
- Build-log instrumentation shape (AC-8).
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import random
import re
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_ROOT / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def load_graph_indexer():
    return _load_module("graph_indexer", "graph_indexer.py")


# ---------------------------------------------------------------------------
# Shared driver: one source tree, an incremental index dir that persists
# across builds, and per-step fresh oracle index dirs.
# ---------------------------------------------------------------------------


class _RepoDriver:
    def __init__(self, mod, root: Path):
        self.mod = mod
        self.root = root
        self.files: dict[str, str] = {}
        self.index_dir = root / ".wavefoundry" / "index"
        self._oracle_seq = 0

    def write(self, rel: str, text: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        self.files[rel] = text

    def delete(self, rel: str) -> None:
        try:
            (self.root / rel).unlink()
        except OSError:
            pass
        self.files.pop(rel, None)

    def _meta(self) -> dict[str, dict[str, str]]:
        return {
            rel: {"hash": hashlib.sha256(text.encode("utf-8")).hexdigest()}
            for rel, text in self.files.items()
        }

    def _build(self, index_dir: Path, changed: set[str], removed: set[str]):
        return self.mod.update_graph_index(
            root=self.root,
            index_dir=index_dir,
            layer="project",
            files=[self.root / rel for rel in sorted(self.files)],
            current_file_meta=self._meta(),
            changed=set(changed),
            removed=set(removed),
            walker_version="1",
            chunker_version="1",
            verbose=False,
        )

    def build_incremental(self, changed: set[str], removed: set[str] | None = None):
        return self._build(self.index_dir, changed, removed or set())

    def build_oracle(self):
        """From-scratch full rebuild of the SAME tree into a fresh index dir."""
        self._oracle_seq += 1
        oracle_dir = self.root / ".wavefoundry" / f"oracle-{self._oracle_seq}"
        return self._build(oracle_dir, set(self.files), set())


def _edge_keys(payload) -> list[tuple[str, str, str, str]]:
    return sorted(
        (
            str(e.get("source") or ""),
            str(e.get("target") or ""),
            str(e.get("relation") or ""),
            str(e.get("confidence") or ""),
        )
        for e in payload.get("edges", [])
    )


def _node_dicts(payload) -> list[dict]:
    return sorted(
        (dict(n) for n in payload.get("nodes", [])),
        key=lambda n: str(n.get("id") or ""),
    )


def _find_edges(payload, *, source_prefix: str = "", target: str | None = None, relation: str | None = None):
    out = []
    for e in payload.get("edges", []):
        if source_prefix and not str(e.get("source") or "").startswith(source_prefix):
            continue
        if target is not None and str(e.get("target") or "") != target:
            continue
        if relation is not None and str(e.get("relation") or "") != relation:
            continue
        out.append(e)
    return out


class _IncrementalMergeBase(unittest.TestCase):
    def setUp(self):
        self.mod = load_graph_indexer()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.driver = _RepoDriver(self.mod, self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def assert_equivalent(self, incremental_payload, oracle_payload, context: str = ""):
        suffix = f" [{context}]" if context else ""
        self.assertEqual(
            _node_dicts(incremental_payload),
            _node_dicts(oracle_payload),
            f"node sets diverge{suffix}",
        )
        self.assertEqual(
            _edge_keys(incremental_payload),
            _edge_keys(oracle_payload),
            f"edge-key sets diverge{suffix}",
        )
        self.assertEqual(
            incremental_payload.get("input_fingerprint"),
            oracle_payload.get("input_fingerprint"),
            f"input_fingerprint diverges{suffix}",
        )


# ---------------------------------------------------------------------------
# GraphStateStore unit tests
# ---------------------------------------------------------------------------


class GraphStateStoreTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_graph_indexer()
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "graph" / "project-graph-state.sqlite"

    def tearDown(self):
        self.tmp.cleanup()

    def _store(self, **kwargs):
        defaults = {"layer": "project", "walker_version": "1", "chunker_version": "1"}
        defaults.update(kwargs)
        return self.mod.GraphStateStore(self.path, **defaults)

    def test_put_get_delete_iterate_roundtrip(self):
        store = self._store()
        store.ensure_current()
        record_a = {"source_hash": "ha", "artifact": {"kind": "code", "path": "a.py", "nodes": [], "edges": []}}
        record_b = {"source_hash": "hb", "artifact": {"kind": "doc", "path": "b.md"}}
        store.apply_build(puts={"a.py": record_a, "b.md": record_b}, deletes=[], blobs={}, meta={})
        self.assertEqual(store.get_record("a.py"), record_a)
        self.assertEqual(store.paths_with_hashes(), {"a.py": "ha", "b.md": "hb"})
        self.assertEqual(dict(store.iter_records()), {"a.py": record_a, "b.md": record_b})
        store.apply_build(puts={}, deletes=["a.py"], blobs={}, meta={})
        self.assertIsNone(store.get_record("a.py"))
        self.assertEqual(store.paths_with_hashes(), {"b.md": "hb"})
        store.close()

    def test_record_bytes_are_gzip_compact_json(self):
        store = self._store()
        store.ensure_current()
        record = {"source_hash": "h", "artifact": {"kind": "code"}}
        store.apply_build(puts={"a.py": record}, deletes=[], blobs={}, meta={})
        raw = store._conn.execute("SELECT record FROM files WHERE path='a.py'").fetchone()[0]
        self.assertEqual(bytes(raw[:2]), b"\x1f\x8b", "record blob must be gzip")
        self.assertEqual(self.mod._decode_state_record(raw), record)
        store.close()

    def test_version_mismatch_resets_whole_store(self):
        store = self._store()
        store.ensure_current()
        store.apply_build(
            puts={"a.py": {"source_hash": "h", "artifact": {}}},
            deletes=[],
            blobs={"merge_state": {"format": "1"}},
            meta={},
        )
        store.close()
        # Reopen with a different walker version: whole-store invalidation.
        store2 = self._store(walker_version="2")
        self.assertFalse(store2.versions_current())
        store2.ensure_current()
        self.assertEqual(store2.paths_with_hashes(), {})
        self.assertIsNone(store2.get_blob("merge_state"))
        self.assertTrue(store2.versions_current())
        store2.close()

    def test_corrupted_database_file_resets_loudly(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_bytes(b"this is not a sqlite database at all........")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            store = self._store()
            store.ensure_current()
        self.assertIn("resetting store", stderr.getvalue())
        self.assertEqual(store.paths_with_hashes(), {})
        store.close()

    def test_io_counters_track_record_granularity(self):
        store = self._store()
        store.ensure_current()
        store.apply_build(
            puts={"a.py": {"source_hash": "h", "artifact": {}}, "b.py": {"source_hash": "h2", "artifact": {}}},
            deletes=[],
            blobs={},
            meta={},
        )
        self.assertEqual(store.record_writes, 2)
        store.get_record("a.py")
        self.assertEqual(store.record_reads, 1)
        # Manifest reads never count as record I/O.
        store.paths_with_hashes()
        self.assertEqual(store.record_reads, 1)
        store.apply_build(puts={}, deletes=["a.py", "b.py"], blobs={}, meta={})
        self.assertEqual(store.record_deletes, 2)
        store.close()

    def test_read_state_builder_version_probe(self):
        index_dir = Path(self.tmp.name) / "idx"
        graph_dir = index_dir / "graph"
        graph_dir.mkdir(parents=True)
        # Nothing present: unknown.
        self.assertEqual(self.mod.read_state_builder_version(index_dir), "")
        # Legacy fallback.
        (graph_dir / "project-graph-state.json").write_text(
            json.dumps({"builder_version": "7"}), encoding="utf-8"
        )
        self.assertEqual(self.mod.read_state_builder_version(index_dir), "7")
        # SQLite store takes precedence once present.
        store = self.mod.GraphStateStore(
            graph_dir / "project-graph-state.sqlite",
            layer="project", walker_version="1", chunker_version="1",
        )
        store.ensure_current()
        store.close()
        self.assertEqual(
            self.mod.read_state_builder_version(index_dir),
            self.mod.GRAPH_BUILDER_VERSION,
        )


# ---------------------------------------------------------------------------
# Randomized differential harness (AC-2)
# ---------------------------------------------------------------------------

_NAME_POOL = ["alpha", "bravo", "casper", "delta_fn", "shared_util", "omega"]
_DIRS = ["pkg_a", "pkg_b"]
# Module basenames deliberately shared across the two package dirs: creating
# `pkg_b/util.py` when `pkg_a/util.py` exists makes every `util.<name>()`
# member call ambiguous — the exact same-name-twin dynamics the symbol-scoped
# invalidation must propagate into untouched files.
_BASENAMES = ["util", "core", "extras", "shared"]


def _render_source(
    defines: list[str],
    calls: list[str],
    imports: list[tuple[str, str]],
    member_calls: list[tuple[str, str]] | None = None,
) -> str:
    member_calls = member_calls or []
    lines: list[str] = []
    for module in sorted({m for m, _ in member_calls}):
        lines.append(f"import {module}")
    for module, name in imports:
        lines.append(f"from {module} import {name}")
    if imports or member_calls:
        lines.append("")
    for name in defines:
        lines.append(f"def {name}():")
        lines.append("    return 1")
        lines.append("")
    if calls or member_calls:
        lines.append("def caller_fn():")
        for name in calls:
            lines.append(f"    {name}()")
        for module, name in member_calls:
            lines.append(f"    {module}.{name}()")
        lines.append("")
    if not lines:
        lines = ["VALUE = 1", ""]
    return "\n".join(lines) + "\n"


class DifferentialEquivalenceTests(_IncrementalMergeBase):
    """AC-2: incremental graph == full-rebuild oracle after every edit step."""

    SEEDS = (1337, 2026, 40961)
    STEPS = 10

    def _random_file_content(self, rng: random.Random) -> str:
        defines = rng.sample(_NAME_POOL, rng.randint(0, 2))
        calls = rng.sample(_NAME_POOL, rng.randint(0, 2))
        # Member calls to the shared module basenames: `util.alpha()` binds
        # while exactly one `util.py` exists and must demote when a twin
        # module appears in the other package dir.
        member_calls = [
            (module, rng.choice(_NAME_POOL))
            for module in rng.sample(_BASENAMES, rng.randint(0, 2))
        ]
        imports: list[tuple[str, str]] = []
        if self.driver.files and rng.random() < 0.4:
            target_rel = rng.choice(sorted(self.driver.files))
            module = target_rel[:-3].replace("/", ".")
            imports.append((module, rng.choice(_NAME_POOL)))
        return _render_source(defines, calls, imports, member_calls)

    def _pick_new_rel(self, rng: random.Random, counter: int) -> str:
        candidates = [
            f"{d}/{b}.py"
            for d in _DIRS
            for b in _BASENAMES
            if f"{d}/{b}.py" not in self.driver.files
        ]
        if candidates and rng.random() < 0.75:
            return rng.choice(sorted(candidates))
        return f"{rng.choice(_DIRS)}/mod_{counter}.py"

    def _run_sequence(self, seed: int):
        rng = random.Random(seed)
        op_log: list[str] = []

        # Seed corpus: same-basename module files with overlapping defined and
        # referenced names (twin-ambiguity-prone by construction).
        seed_rels = ["pkg_a/util.py", "pkg_a/core.py", "pkg_b/extras.py", "pkg_a/mod_0.py", "pkg_b/mod_1.py"]
        for rel in seed_rels:
            self.driver.write(rel, self._random_file_content(rng))
            op_log.append(f"seed {rel}")
        payload = self.driver.build_incremental(set(self.driver.files))
        oracle = self.driver.build_oracle()
        self.assert_equivalent(payload, oracle, f"seed={seed} after corpus seed: {op_log}")

        counter = 100
        for step in range(self.STEPS):
            ops = ["add", "modify", "modify", "delete"]
            op = rng.choice(ops)
            if op == "delete" and len(self.driver.files) <= 2:
                op = "add"
            if op == "add":
                counter += 1
                rel = self._pick_new_rel(rng, counter)
                self.driver.write(rel, self._random_file_content(rng))
                changed, removed = {rel}, set()
                op_log.append(f"add {rel}")
            elif op == "modify":
                rel = rng.choice(sorted(self.driver.files))
                self.driver.write(rel, self._random_file_content(rng))
                changed, removed = {rel}, set()
                op_log.append(f"modify {rel}")
            else:
                rel = rng.choice(sorted(self.driver.files))
                self.driver.delete(rel)
                changed, removed = set(), {rel}
                op_log.append(f"delete {rel}")
            payload = self.driver.build_incremental(changed, removed)
            oracle = self.driver.build_oracle()
            self.assert_equivalent(
                payload,
                oracle,
                f"seed={seed} step={step} sequence={op_log}",
            )

    def test_differential_equivalence_seed_1337(self):
        self._run_sequence(1337)

    def test_differential_equivalence_seed_2026(self):
        self._run_sequence(2026)

    def test_differential_equivalence_seed_40961(self):
        self._run_sequence(40961)


# ---------------------------------------------------------------------------
# Targeted twin-flip faithfulness (AC-3)
# ---------------------------------------------------------------------------


class TwinFlipFaithfulnessTests(_IncrementalMergeBase):
    # The Python extractor only emits a calls edge when the callee is locally
    # known, imported, or a member expression — a bare call to an unknown name
    # is (deliberately) not an edge. The twin fixtures therefore use the
    # `import helpers` + `helpers.helper()` member form, whose
    # `external::helpers.helper` target resolves through the dotted-suffix
    # candidate index — unique module basename binds, twin module demotes.

    _CALLER = "import helpers\n\ndef run():\n    helpers.helper()\n"

    def test_adding_second_twin_demotes_untouched_files_bound_edge(self):
        self.driver.write("pkg_a/helpers.py", "def helper():\n    return 1\n")
        self.driver.write("caller.py", self._CALLER)
        payload = self.driver.build_incremental(set(self.driver.files))
        bound = _find_edges(payload, source_prefix="caller.py", target="pkg_a/helpers.py::helper", relation="calls")
        self.assertTrue(bound, "unique helpers.helper() must bind cross-file")
        self.assertEqual(bound[0]["confidence"], "RECEIVER_RESOLVED", "exact-unique bind promotes")

        # Add a same-name twin MODULE in the other package; caller.py untouched.
        self.driver.write("pkg_b/helpers.py", "def helper():\n    return 2\n")
        payload = self.driver.build_incremental({"pkg_b/helpers.py"})
        self.assertFalse(
            _find_edges(payload, source_prefix="caller.py", target="pkg_a/helpers.py::helper"),
            "ambiguous helpers.helper() must DEMOTE the previously-bound edge in the untouched file",
        )
        external = _find_edges(payload, source_prefix="caller.py", target="external::helpers.helper", relation="calls")
        self.assertTrue(external, "demoted edge returns to external::helpers.helper")
        self.assertEqual(external[0]["confidence"], "EXTRACTED", "demotion restores the raw confidence")
        self.assert_equivalent(payload, self.driver.build_oracle(), "after twin add")

    def test_deleting_twin_promotes_untouched_files_external_edge(self):
        self.driver.write("pkg_a/helpers.py", "def helper():\n    return 1\n")
        self.driver.write("pkg_b/helpers.py", "def helper():\n    return 2\n")
        self.driver.write("caller.py", self._CALLER)
        payload = self.driver.build_incremental(set(self.driver.files))
        self.assertTrue(
            _find_edges(payload, source_prefix="caller.py", target="external::helpers.helper"),
            "ambiguous helpers.helper() must stay external",
        )

        self.driver.delete("pkg_b/helpers.py")
        payload = self.driver.build_incremental(set(), removed={"pkg_b/helpers.py"})
        bound = _find_edges(payload, source_prefix="caller.py", target="pkg_a/helpers.py::helper", relation="calls")
        self.assertTrue(bound, "now-unique helpers.helper() must PROMOTE in the untouched caller")
        self.assertEqual(bound[0]["confidence"], "RECEIVER_RESOLVED")
        self.assert_equivalent(payload, self.driver.build_oracle(), "after twin delete")

    def test_import_disambiguation_rebinds_on_import_change(self):
        self.driver.write("m1.py", "def helper():\n    return 1\n")
        self.driver.write("m2.py", "def helper():\n    return 2\n")
        self.driver.write(
            "caller.py",
            "from m1 import helper\n\ndef run():\n    helper()\n",
        )
        payload = self.driver.build_incremental(set(self.driver.files))
        self.assertTrue(
            _find_edges(payload, source_prefix="caller.py", target="m1.py::helper", relation="calls"),
            "import-qualified call binds to the imported twin",
        )

        # Flip the import: the edge must follow to the other twin.
        self.driver.write(
            "caller.py",
            "from m2 import helper\n\ndef run():\n    helper()\n",
        )
        payload = self.driver.build_incremental({"caller.py"})
        self.assertTrue(
            _find_edges(payload, source_prefix="caller.py", target="m2.py::helper", relation="calls"),
            "import flip rebinds to the other twin",
        )
        self.assertFalse(
            _find_edges(payload, source_prefix="caller.py", target="m1.py::helper"),
            "old binding released",
        )
        self.assert_equivalent(payload, self.driver.build_oracle(), "after import flip")

    def test_import_edge_disambiguation_survives_third_twin_addition(self):
        """Cross-file scope (b): adding a third twin re-runs disambiguation for
        the untouched importer, whose import still uniquely identifies m1."""
        self.driver.write("m1.py", "def helper():\n    return 1\n")
        self.driver.write("m2.py", "def helper():\n    return 2\n")
        self.driver.write(
            "caller.py",
            "from m1 import helper\n\ndef run():\n    helper()\n",
        )
        payload = self.driver.build_incremental(set(self.driver.files))
        self.assertTrue(_find_edges(payload, source_prefix="caller.py", target="m1.py::helper"))
        self.driver.write("m3.py", "def helper():\n    return 3\n")
        payload = self.driver.build_incremental({"m3.py"})
        self.assertTrue(
            _find_edges(payload, source_prefix="caller.py", target="m1.py::helper"),
            "import-disambiguated bind must survive a third twin",
        )
        self.assert_equivalent(payload, self.driver.build_oracle(), "after third twin")

    def test_rename_releases_old_name_and_binds_new(self):
        self.driver.write("pkg_a/helpers.py", "def old_name():\n    return 1\n")
        self.driver.write("caller.py", "import helpers\n\ndef run():\n    helpers.old_name()\n")
        payload = self.driver.build_incremental(set(self.driver.files))
        self.assertTrue(_find_edges(payload, source_prefix="caller.py", target="pkg_a/helpers.py::old_name"))

        # Rename in the definer; the untouched caller's edge must release.
        self.driver.write("pkg_a/helpers.py", "def new_name():\n    return 1\n")
        payload = self.driver.build_incremental({"pkg_a/helpers.py"})
        self.assertFalse(
            _find_edges(payload, source_prefix="caller.py", target="pkg_a/helpers.py::old_name"),
            "renamed-away symbol must not stay bound",
        )
        self.assertTrue(
            _find_edges(payload, source_prefix="caller.py", target="external::helpers.old_name"),
            "released edge returns to external",
        )
        self.assert_equivalent(payload, self.driver.build_oracle(), "after rename release")

        # Update the caller to the new name: binds.
        self.driver.write("caller.py", "import helpers\n\ndef run():\n    helpers.new_name()\n")
        payload = self.driver.build_incremental({"caller.py"})
        self.assertTrue(
            _find_edges(payload, source_prefix="caller.py", target="pkg_a/helpers.py::new_name"),
            "new name binds",
        )
        self.assert_equivalent(payload, self.driver.build_oracle(), "after rename bind")

    def test_doc_reference_follows_symbol_changes(self):
        """Doc-impact semantics preserved through the incremental pipeline."""
        self.driver.write("src/tools.py", "def process():\n    return 1\n")
        self.driver.write("docs/guide.md", "Call `process` from the guide.\n")
        payload = self.driver.build_incremental(set(self.driver.files))
        self.assertTrue(
            _find_edges(payload, source_prefix="docs/guide.md", relation="doc_references_code")
        )
        # Removing the symbol rescans the doc (mentioned ∩ changed) — the
        # reference must drop without the doc itself changing.
        self.driver.write("src/tools.py", "def handler():\n    return 1\n")
        payload = self.driver.build_incremental({"src/tools.py"})
        self.assertFalse(
            _find_edges(payload, source_prefix="docs/guide.md", relation="doc_references_code"),
            "doc edge to the removed symbol must drop",
        )


# ---------------------------------------------------------------------------
# Same-file qualification-depth swaps (adversarial faithfulness regression)
# ---------------------------------------------------------------------------


class DepthSwapDeltaKeyTests(_IncrementalMergeBase):
    """Regression: the symbol delta must be computed PER SIDE (old ∪ new).

    A single merged old+new subset lets _build_candidate_indexes pick one
    winner per (file, simple name), dropping the loser node's qualified keys
    from the delta — so an untouched file's `reads` edge (exact bare lookup
    only) escaped scope (b) re-resolution when the definer swapped a symbol
    across qualification depths (top-level CONST <-> Class.CONST). Found by
    the wave-review adversarial faithfulness lane (P5/P6 probes).
    """

    _CALLER = "from pkg.mod.Config import CONST\n\ndef frun():\n    return CONST\n"

    def test_depth_swap_promotes_reads_edge_in_untouched_file(self):
        # P5: top-level CONST -> class Config: CONST must re-resolve the
        # untouched caller's reads edge to the new qualified node.
        self.driver.write("caller.py", self._CALLER)
        self.driver.write("pkg/mod.py", "CONST = 1\n")
        self.driver.build_incremental(set(self.driver.files))

        self.driver.write("pkg/mod.py", "class Config:\n    CONST = 2\n")
        incremental = self.driver.build_incremental({"pkg/mod.py"})
        oracle = self.driver.build_oracle()
        self.assert_equivalent(incremental, oracle, "P5 depth swap up")
        self.assertTrue(
            _find_edges(
                incremental,
                source_prefix="caller.py",
                target="pkg/mod.py::Config.CONST",
                relation="reads",
            ),
            "untouched caller's reads edge must bind the new qualified node",
        )

    def test_reverse_depth_swap_never_resurrects_dangling_edge(self):
        # P6: Class.CONST -> top-level CONST demotes the bound edge; a later
        # unrelated edit must NOT resurrect a stale fragment edge pointing at
        # the no-longer-existing qualified node.
        self.driver.write("caller.py", self._CALLER)
        self.driver.write("pkg/mod.py", "class Config:\n    CONST = 2\n")
        self.driver.write("z.py", "def zfn():\n    return 0\n")
        self.driver.build_incremental(set(self.driver.files))

        self.driver.write("pkg/mod.py", "CONST = 1\n")
        incremental = self.driver.build_incremental({"pkg/mod.py"})
        self.assert_equivalent(incremental, self.driver.build_oracle(), "P6 swap down")

        self.driver.write("z.py", "def zfn():\n    return 1\n")
        incremental = self.driver.build_incremental({"z.py"})
        oracle = self.driver.build_oracle()
        self.assert_equivalent(incremental, oracle, "P6 unrelated edit")
        node_ids = {str(n.get("id") or "") for n in incremental.get("nodes", [])}
        for edge in incremental.get("edges", []):
            target = str(edge.get("target") or "")
            if not target.startswith("external::"):
                self.assertIn(
                    target, node_ids,
                    f"edge target {target!r} dangles (stale fragment resurrected)",
                )


# ---------------------------------------------------------------------------
# Version invalidation + legacy migration (AC-4)
# ---------------------------------------------------------------------------


class VersionAndMigrationTests(_IncrementalMergeBase):
    def _store_path(self) -> Path:
        return self.driver.index_dir / "graph" / "project-graph-state.sqlite"

    def _legacy_path(self) -> Path:
        return self.driver.index_dir / "graph" / "project-graph-state.json"

    def test_builder_version_mismatch_forces_full_reextract(self):
        self.driver.write("a.py", "def alpha():\n    return 1\n")
        self.driver.write("b.py", "def run():\n    alpha()\n")
        first = self.driver.build_incremental(set(self.driver.files))
        self.assertTrue(first.get("nodes"))
        # Poke an older builder_version into the store meta.
        conn = sqlite3.connect(str(self._store_path()))
        with conn:
            conn.execute("UPDATE meta SET value='0' WHERE key='builder_version'")
        conn.close()
        # A build with NO changed files must still recover the full corpus
        # (whole-store invalidation → empty state → corpus expansion).
        payload = self.driver.build_incremental(set())
        self.assertEqual(
            {n["id"] for n in first["nodes"]},
            {n["id"] for n in payload["nodes"]},
            "version mismatch must re-extract the full corpus",
        )
        self.assertEqual(
            self.mod.read_state_builder_version(self.driver.index_dir),
            self.mod.GRAPH_BUILDER_VERSION,
        )

    def test_legacy_monolithic_state_discarded_once_idempotently(self):
        self.driver.write("a.py", "def alpha():\n    return 1\n")
        legacy = self._legacy_path()
        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_text(json.dumps({"builder_version": "35", "files": {}}), encoding="utf-8")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            payload = self.driver.build_incremental(set(self.driver.files))
        self.assertIn("legacy monolithic graph state discarded", stderr.getvalue())
        self.assertFalse(legacy.exists(), "legacy state must be discarded")
        self.assertTrue(self._store_path().exists(), "store must be seeded")
        self.assertTrue(payload.get("nodes"))
        # Second build: no legacy file, no discard message — idempotent.
        stderr2 = io.StringIO()
        with contextlib.redirect_stderr(stderr2):
            self.driver.build_incremental(set())
        self.assertNotIn("legacy monolithic graph state discarded", stderr2.getvalue())
        self.assertFalse(legacy.exists())


# ---------------------------------------------------------------------------
# Crash consistency (AC-5)
# ---------------------------------------------------------------------------


class CrashConsistencyTests(_IncrementalMergeBase):
    def _seed(self):
        self.driver.write("pkg_a/definer.py", "def helper():\n    return 1\n")
        self.driver.write("pkg_a/caller.py", "def run():\n    helper()\n")
        return self.driver.build_incremental(set(self.driver.files))

    def test_abort_inside_store_transaction_rolls_back_cleanly(self):
        """Interrupted between per-file writes: the transaction aborts whole,
        the previous state stays intact, and the next build recovers."""
        self._seed()
        conn = sqlite3.connect(str(self.driver.index_dir / "graph" / "project-graph-state.sqlite"))
        before = dict(conn.execute("SELECT path, source_hash FROM files"))
        conn.close()

        self.driver.write("pkg_a/definer.py", "def helper():\n    return 2\n")
        original = self.mod._encode_state_record
        calls = {"n": 0}

        def _boom(payload):
            calls["n"] += 1
            raise RuntimeError("injected mid-transaction fault")

        self.mod._encode_state_record = _boom
        try:
            with self.assertRaises(RuntimeError):
                self.driver.build_incremental({"pkg_a/definer.py"})
        finally:
            self.mod._encode_state_record = original
        self.assertGreater(calls["n"], 0)

        conn = sqlite3.connect(str(self.driver.index_dir / "graph" / "project-graph-state.sqlite"))
        after = dict(conn.execute("SELECT path, source_hash FROM files"))
        conn.close()
        self.assertEqual(before, after, "aborted transaction must roll back completely")

        # Next build (same pending change) succeeds and equals the oracle.
        payload = self.driver.build_incremental({"pkg_a/definer.py"})
        self.assert_equivalent(payload, self.driver.build_oracle(), "after rollback recovery")

    def test_crash_between_store_commit_and_payload_write_degrades_loudly(self):
        self._seed()
        self.driver.write("pkg_a/definer.py", "def helper():\n    return 3\n")
        original = self.mod._write_json
        graph_name = "project-graph.json"

        def _boom(path, payload):
            if path.name == graph_name:
                raise RuntimeError("injected crash before payload write")
            return original(path, payload)

        self.mod._write_json = _boom
        try:
            with self.assertRaises(RuntimeError):
                self.driver.build_incremental({"pkg_a/definer.py"})
        finally:
            self.mod._write_json = original

        # Store committed but payload was never rewritten: the binding is
        # pending → next build detects it, degrades loudly to a full re-merge
        # from the (newer) rows, and converges with the oracle.
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            payload = self.driver.build_incremental(set())
        self.assertIn("full re-merge", stderr.getvalue())
        self.assert_equivalent(payload, self.driver.build_oracle(), "after payload-write crash")

    def test_crash_before_binding_stat_commit_degrades_loudly(self):
        self._seed()
        self.driver.write("pkg_a/definer.py", "def helper():\n    return 4\n")
        original = self.mod.GraphStateStore.set_meta

        def _boom(store_self, updates):
            raise RuntimeError("injected crash before binding commit")

        self.mod.GraphStateStore.set_meta = _boom
        try:
            with self.assertRaises(RuntimeError):
                self.driver.build_incremental({"pkg_a/definer.py"})
        finally:
            self.mod.GraphStateStore.set_meta = original

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            payload = self.driver.build_incremental(set())
        self.assertIn("full re-merge", stderr.getvalue())
        self.assert_equivalent(payload, self.driver.build_oracle(), "after binding-commit crash")

    def test_payload_deleted_out_of_band_recovers_loudly(self):
        self._seed()
        (self.driver.index_dir / "graph" / "project-graph.json").unlink()
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            payload = self.driver.build_incremental(set())
        self.assertIn("full re-merge", stderr.getvalue())
        self.assert_equivalent(payload, self.driver.build_oracle(), "after payload deletion")


# ---------------------------------------------------------------------------
# Zero-change fast path + O(changed) state I/O (AC-1)
# ---------------------------------------------------------------------------


class DeltaCostTests(_IncrementalMergeBase):
    def test_zero_change_build_rewrites_nothing(self):
        self.driver.write("a.py", "def alpha():\n    return 1\n")
        self.driver.write("b.py", "def run():\n    alpha()\n")
        self.driver.build_incremental(set(self.driver.files))
        graph_path = self.driver.index_dir / "graph" / "project-graph.json"
        store_path = self.driver.index_dir / "graph" / "project-graph-state.sqlite"
        payload_stat = graph_path.stat().st_mtime_ns
        store_size = store_path.stat().st_size

        payload = self.driver.build_incremental(set())
        stats = payload.get("merge_stats") or {}
        self.assertEqual(stats.get("mode"), "zero-change")
        self.assertEqual(stats.get("state_reads"), 0)
        self.assertEqual(stats.get("state_writes"), 0)
        self.assertEqual(stats.get("blob_writes"), 0, "zero-change must not rewrite the sidecar")
        self.assertEqual(stats.get("blob_bytes"), 0)
        self.assertEqual(
            graph_path.stat().st_mtime_ns, payload_stat, "zero-change build must not rewrite the payload"
        )
        self.assertEqual(store_path.stat().st_size, store_size)

    def test_one_file_edit_touches_only_changed_rows(self):
        for k in range(6):
            self.driver.write(f"pkg_a/mod_{k}.py", f"def fn_{k}():\n    return {k}\n")
        self.driver.build_incremental(set(self.driver.files))

        self.driver.write("pkg_a/mod_3.py", "def fn_3():\n    return 33\n")
        payload = self.driver.build_incremental({"pkg_a/mod_3.py"})
        stats = payload.get("merge_stats") or {}
        self.assertEqual(stats.get("mode"), "incremental")
        self.assertEqual(stats.get("state_reads"), 0, "no unchanged row may be read")
        self.assertEqual(stats.get("state_writes"), 1, "exactly the changed row is written")
        self.assertEqual(stats.get("files_changed"), 1)
        # The merge_state sidecar is O(graph) per changed build BY DESIGN
        # (it is the persistent merged map); the counters must make that
        # term visible rather than hiding it behind row counts
        # (delivery-review finding: `state io: writes=1` under-reported the
        # dominant byte term).
        self.assertEqual(stats.get("blob_reads"), 1, "sidecar read must be counted")
        self.assertEqual(stats.get("blob_writes"), 1, "sidecar rewrite must be counted")
        self.assertGreater(stats.get("blob_bytes"), 0, "sidecar bytes must be visible")
        self.assert_equivalent(payload, self.driver.build_oracle(), "one-file edit")

    def test_merge_stats_shape(self):
        self.driver.write("a.py", "def alpha():\n    return 1\n")
        payload = self.driver.build_incremental(set(self.driver.files))
        stats = payload.get("merge_stats") or {}
        for key in (
            "mode",
            "merge_ms",
            "files_changed",
            "files_removed",
            "symbols_invalidated",
            "edges_reresolved",
            "state_reads",
            "state_writes",
            "blob_reads",
            "blob_writes",
            "blob_bytes",
        ):
            self.assertIn(key, stats)
        # The persisted payload must NOT carry merge stats.
        on_disk = self.mod.read_graph_payload(self.root, "project")
        self.assertNotIn("merge_stats", on_disk)


# ---------------------------------------------------------------------------
# Fingerprint-gated analysis skip (AC-6)
# ---------------------------------------------------------------------------


class FingerprintAnalysisSkipTests(unittest.TestCase):
    def setUp(self):
        self.gc = _load_module("graph_cluster_under_test", "graph_cluster.py")
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.index_dir = self.root / ".wavefoundry" / "index"

    def tearDown(self):
        self.tmp.cleanup()

    def _graph(self, fingerprint: str, extra_edge: bool = False):
        nodes = [
            {"id": "a.py", "label": "a", "kind": "module", "source_file": "a.py", "source_location": "1:0", "layer": "project"},
            {"id": "a.py::fn", "label": "fn", "kind": "function", "source_file": "a.py", "source_location": "2:0", "layer": "project"},
            {"id": "b.py", "label": "b", "kind": "module", "source_file": "b.py", "source_location": "1:0", "layer": "project"},
        ]
        edges = [
            {"source": "a.py", "target": "a.py::fn", "relation": "defines", "confidence": "EXTRACTED"},
            {"source": "b.py", "target": "a.py::fn", "relation": "calls", "confidence": "EXTRACTED"},
        ]
        if extra_edge:
            edges.append({"source": "a.py", "target": "b.py", "relation": "imports", "confidence": "EXTRACTED"})
        return {
            "schema_version": "1",
            "builder_version": "36",
            "layer": "project",
            "input_fingerprint": fingerprint,
            "nodes": nodes,
            "edges": edges,
            "counts": {"files": 2, "nodes": len(nodes), "edges": len(edges)},
        }

    def _update(self, graph):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            payload = self.gc.update_graph_clusters(
                root=self.root,
                index_dir=self.index_dir,
                layer="project",
                graph_payload=graph,
                verbose=False,
            )
        return payload, stderr.getvalue()

    def test_unchanged_fingerprint_skips_recompute_and_rewrite(self):
        first, _ = self._update(self._graph("fp-one"))
        cluster_path = self.gc.cluster_path(self.root, "project")
        self.assertTrue(cluster_path.exists())
        stat_before = cluster_path.stat().st_mtime_ns

        second, err = self._update(self._graph("fp-one"))
        self.assertIn("fingerprint match", err)
        self.assertEqual(
            cluster_path.stat().st_mtime_ns,
            stat_before,
            "unchanged fingerprint must not rewrite the clusters artifact",
        )
        self.assertEqual(first.get("community_count"), second.get("community_count"))

    def test_changed_fingerprint_recomputes(self):
        self._update(self._graph("fp-one"))
        cluster_path = self.gc.cluster_path(self.root, "project")
        stat_before = cluster_path.stat().st_mtime_ns
        _, err = self._update(self._graph("fp-two", extra_edge=True))
        self.assertNotIn("fingerprint match", err)
        self.assertNotEqual(
            cluster_path.stat().st_mtime_ns,
            stat_before,
            "changed fingerprint must refresh the artifact",
        )
        payload = self.gc.read_cluster_payload(self.root, "project")
        self.assertEqual(payload.get("input_fingerprint"), "fp-two")

    def test_cluster_builder_version_change_recomputes(self):
        self._update(self._graph("fp-one"))
        cluster_path = self.gc.cluster_path(self.root, "project")
        # Rewrite the artifact as if produced by an older cluster builder.
        existing = self.gc._read_json(cluster_path, {})
        existing["cluster_builder_version"] = "0"
        self.gc._write_json(cluster_path, existing)
        stat_before = cluster_path.stat().st_mtime_ns
        _, err = self._update(self._graph("fp-one"))
        self.assertNotIn("fingerprint match", err)
        self.assertNotEqual(cluster_path.stat().st_mtime_ns, stat_before)


# ---------------------------------------------------------------------------
# Build-log instrumentation (AC-8)
# ---------------------------------------------------------------------------


class BuildLogInstrumentationTests(unittest.TestCase):
    def setUp(self):
        self.idx = _load_module("indexer_for_merge_log_test", "indexer.py")
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_finished_graph_line_reports_merge_delta_and_state_io(self):
        src = self.root / "src" / "tools.py"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("def process():\n    return 1\n", encoding="utf-8")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.idx._build_graph_artifacts(
                root=self.root,
                index_dir=self.root / ".wavefoundry" / "index",
                layer="project",
                files=[src],
                current_file_meta={"src/tools.py": {"hash": "h1"}},
                changed={"src/tools.py"},
                removed=set(),
                walker_version="1",
                chunker_version="1",
                verbose=False,
            )
        line = next(
            (l for l in stderr.getvalue().splitlines() if "finished graph" in l),
            "",
        )
        self.assertRegex(
            line,
            r"merge\[(incremental|full-merge|zero-change)\]: \d+\.\ds"
            r" \| delta: files=\d+ removed=\d+ symbols=\d+ edges_reresolved=\d+"
            r" \| state io: reads=\d+ writes=\d+"
            r" \| sidecar: reads=\d+ writes=\d+ bytes=\d+",
        )


if __name__ == "__main__":
    unittest.main()
