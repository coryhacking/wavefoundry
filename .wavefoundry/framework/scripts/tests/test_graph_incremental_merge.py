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
from unittest.mock import patch

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))
import index_paths  # noqa: E402 — one definition of the shared database name


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_ROOT / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def load_graph_indexer():
    return _load_module("graph_indexer", "graph_indexer.py")


def load_index_state_store():
    import index_state_store

    return index_state_store


def load_sqlite_runtime():
    import sqlite_runtime

    return sqlite_runtime


def load_graph_store():
    import graph_store

    return graph_store


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

    def _visible(self, rel: str, unreadable_dirs: set[str] | None) -> bool:
        for d in unreadable_dirs or ():
            d = d.rstrip("/")
            if rel == d or rel.startswith(d + "/"):
                return False
        return True

    def _build(
        self,
        index_dir: Path,
        changed: set[str],
        removed: set[str],
        unreadable_dirs: set[str] | None = None,
    ):
        # Wave 1x6ti (1x5pc): `unreadable_dirs` models a walk outage the way
        # the indexer's walk hands it to the session -- the shadowed subtree
        # is absent from `files` and `current_file_meta` (the walk never saw
        # it) and the directories are reported so the merge keeps the known
        # rows as current instead of pruning them.
        visible = {
            rel: text
            for rel, text in self.files.items()
            if self._visible(rel, unreadable_dirs)
        }
        meta = {
            rel: {"hash": hashlib.sha256(text.encode("utf-8")).hexdigest()}
            for rel, text in visible.items()
        }
        return self.mod.update_graph_index(
            root=self.root,
            index_dir=index_dir,
            layer="project",
            files=[self.root / rel for rel in sorted(visible)],
            current_file_meta=meta,
            changed=set(changed),
            removed=set(removed),
            walker_version="1",
            chunker_version="1",
            verbose=False,
            unreadable_dirs=set(unreadable_dirs) if unreadable_dirs else None,
        )

    def build_incremental(
        self,
        changed: set[str],
        removed: set[str] | None = None,
        unreadable_dirs: set[str] | None = None,
    ):
        return self._build(self.index_dir, changed, removed or set(), unreadable_dirs)

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


class _SharedStore:
    """Open the graph state reader on a real shared index connection.

    Wave 1xny6: ``GraphStateStore`` no longer opens anything -- it reads
    through the caller's ``sqlite_runtime`` connection. Tests therefore open
    an ``IndexStateStore`` the way the build coordinator does and hand its
    connection over, which is also what makes the single-binding rule
    testable: there is no second SQLite library anywhere in this path.
    """

    def __init__(self, mod, index_dir: Path, **kwargs):
        self.mod = mod
        defaults = {"layer": "project", "walker_version": "1", "chunker_version": "1"}
        defaults.update(kwargs)
        self.iss = load_index_state_store()
        self.state = self.iss.IndexStateStore(index_dir)
        self.store = mod.GraphStateStore(self.state._conn, **defaults)

    @property
    def conn(self):
        return self.state._conn

    def publish(self, publication, *, settle: bool = True) -> None:
        """Apply a prepared publication in one transaction, as a caller does.

        ``settle`` mirrors what a real build does across session boundaries:
        once the rebuilt rows commit, the owed reset is no longer pending and
        the next session's version gate passes. Pass ``settle=False`` to keep
        observing the pre-commit view.
        """
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            publication.apply(self.conn)
            self.conn.execute("COMMIT")
        except BaseException:
            self.conn.execute("ROLLBACK")
            raise
        if settle:
            self.store.reset_pending = False

    def close(self):
        self.store.close()
        self.state.close()


def make_publication(mod, *, layer="project", **kwargs):
    """A minimal GraphPublication for store-level unit tests."""
    return mod.GraphPublication(layer=layer, **kwargs)


def file_publication(mod, store, puts: dict, deletes=(), meta=None):
    """Publish file-extraction rows the way ``_prepare_publication`` would."""
    return mod.GraphPublication(
        layer="project",
        file_puts={
            rel: (str(rec.get("source_hash") or ""), mod._encode_state_record(rec))
            for rel, rec in puts.items()
        },
        file_deletes=list(deletes),
        meta=meta if meta is not None else dict(store._expected_versions()),
    )


class GraphStateStoreTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_graph_indexer()
        self.tmp = tempfile.TemporaryDirectory()
        self.index_dir = Path(self.tmp.name) / ".wavefoundry" / "index"
        self.shared = _SharedStore(self.mod, self.index_dir)
        self.store = self.shared.store

    def tearDown(self):
        try:
            self.shared.close()
        except Exception:
            pass
        self.tmp.cleanup()

    def test_put_get_delete_iterate_roundtrip(self):
        self.store.ensure_current()
        record_a = {"source_hash": "ha", "artifact": {"kind": "code", "path": "a.py", "nodes": [], "edges": []}}
        record_b = {"source_hash": "hb", "artifact": {"kind": "doc", "path": "b.md"}}
        self.shared.publish(file_publication(
            self.mod, self.store, {"a.py": record_a, "b.md": record_b}))
        self.assertEqual(self.store.get_record("a.py"), record_a)
        self.assertEqual(self.store.paths_with_hashes(), {"a.py": "ha", "b.md": "hb"})
        self.assertEqual(dict(self.store.iter_records()), {"a.py": record_a, "b.md": record_b})
        self.shared.publish(file_publication(self.mod, self.store, {}, deletes=["a.py"]))
        self.assertIsNone(self.store.get_record("a.py"))
        self.assertEqual(self.store.paths_with_hashes(), {"b.md": "hb"})

    def test_record_bytes_are_gzip_compact_json(self):
        self.store.ensure_current()
        record = {"source_hash": "h", "artifact": {"kind": "code"}}
        self.shared.publish(file_publication(self.mod, self.store, {"a.py": record}))
        raw = self.shared.conn.execute(
            "SELECT record FROM graph_file_state WHERE path='a.py'").fetchone()[0]
        self.assertEqual(bytes(raw[:2]), b"\x1f\x8b", "record blob must be gzip")
        self.assertEqual(self.mod._decode_state_record(raw), record)

    def test_graph_meta_is_namespaced_and_never_collides_with_the_semantic_pin(self):
        """The store shares `meta` with the semantic store; a bare
        `store_schema_version` write would overwrite the resident schema pin
        and make the next open refuse the whole database."""
        self.store.ensure_current()
        self.shared.publish(file_publication(self.mod, self.store, {}))
        resident = self.shared.conn.execute(
            "SELECT value FROM meta WHERE key='store_schema_version'").fetchone()
        self.assertEqual(resident[0], load_index_state_store().STATE_STORE_SCHEMA_VERSION)
        self.assertEqual(
            self.store.meta_all()["store_schema_version"],
            self.mod.GRAPH_STORE_SCHEMA_VERSION,
        )
        self.assertNotEqual(resident[0], self.mod.GRAPH_STORE_SCHEMA_VERSION)

    def test_version_mismatch_defers_the_reset_to_the_publication_transaction(self):
        """A builder/walker bump must not erase the readable generation at
        session open; the previous rows stay queryable until the rebuilt rows
        commit (wave 1xny6, Graph extraction row)."""
        self.store.ensure_current()
        record = {"source_hash": "h", "artifact": {}}
        self.shared.publish(file_publication(self.mod, self.store, {"a.py": record}))
        self.shared.close()

        shared2 = _SharedStore(self.mod, self.index_dir, walker_version="2")
        self.addCleanup(shared2.close)
        store2 = shared2.store
        self.assertFalse(store2.versions_current())
        self.assertFalse(store2.ensure_current())
        self.assertTrue(store2.reset_pending)
        # The stale generation reads as empty to the MERGE ...
        self.assertEqual(store2.paths_with_hashes(), {})
        self.assertIsNone(store2.read_merge_state())
        # ... but is still physically present for every other reader.
        rows = shared2.conn.execute("SELECT COUNT(*) FROM graph_file_state").fetchone()[0]
        self.assertEqual(rows, 1, "the previous generation must stay readable")

        # The reset lands only when the rebuilt rows commit.
        plan = self.mod.GraphPublication(
            layer="project", reset=True,
            file_puts={"b.py": ("h2", self.mod._encode_state_record(record))},
            meta=dict(store2._expected_versions()),
        )
        shared2.publish(plan, settle=False)
        self.assertEqual(
            dict(shared2.conn.execute("SELECT path, source_hash FROM graph_file_state")),
            {"b.py": "h2"},
        )
        store2.reset_pending = False
        self.assertTrue(store2.versions_current())

    def test_failed_reset_publication_leaves_the_previous_generation_intact(self):
        self.store.ensure_current()
        record = {"source_hash": "h", "artifact": {}}
        self.shared.publish(file_publication(self.mod, self.store, {"a.py": record}))
        plan = self.mod.GraphPublication(
            layer="project", reset=True,
            file_puts={"b.py": ("h2", self.mod._encode_state_record(record))},
            meta=dict(self.store._expected_versions()),
        )
        original = plan.apply

        def _boom(conn):
            original(conn)
            raise RuntimeError("injected fault after the scoped reset")

        plan.apply = _boom
        with self.assertRaises(RuntimeError):
            self.shared.publish(plan)
        self.assertEqual(
            dict(self.shared.conn.execute("SELECT path, source_hash FROM graph_file_state")),
            {"a.py": "h"},
            "a failed attempt must not publish, not even its reset",
        )

    def test_busy_open_propagates_instead_of_deleting_the_store(self):
        """Memory 1wys2-mem: treating a busy timeout as corruption once
        destroyed a healthy store. The delete-and-recreate arm is gone; the
        open is `IndexStateStore._open`, which preserves the file and lets the
        wait condition surface."""
        sqlite_runtime = load_sqlite_runtime()
        iss = load_index_state_store()
        path = iss.state_store_path(self.index_dir)
        size_before = path.stat().st_size
        blocker = sqlite_runtime.connect(path)
        blocker.execute("BEGIN EXCLUSIVE")
        blocker.execute(
            "INSERT INTO meta (key, value) VALUES ('1xny6-probe','1') "
            "ON CONFLICT(key) DO UPDATE SET value='1'")
        try:
            with self.assertRaises(Exception) as ctx:
                other = iss.IndexStateStore(self.index_dir)
                # _create_tables writes; the held EXCLUSIVE lock blocks it.
                other._conn.execute("BEGIN IMMEDIATE")
            self.assertNotIsInstance(ctx.exception, sqlite_runtime.CorruptionError or ())
        finally:
            blocker.execute("ROLLBACK")
            blocker.close()
        self.assertTrue(path.exists(), "a busy store must never be deleted")
        self.assertGreaterEqual(path.stat().st_size, size_before)

    def test_structural_corruption_returns_the_typed_recovery_response(self):
        sqlite_runtime = load_sqlite_runtime()
        iss = load_index_state_store()
        self.shared.close()
        path = iss.state_store_path(self.index_dir)
        for suffix in ("-wal", "-shm"):
            Path(str(path) + suffix).unlink(missing_ok=True)
        path.write_bytes(b"this is not a sqlite database at all........")
        with self.assertRaises((sqlite_runtime.StorageRecoveryRequired,) + tuple(sqlite_runtime.CorruptionError)):
            iss.IndexStateStore(self.index_dir)
        self.assertTrue(path.exists(), "a corrupt store is preserved, never unlinked")
        self.shared = _SharedStore.__new__(_SharedStore)  # tearDown guard

    def test_io_counters_track_record_granularity(self):
        self.store.ensure_current()
        self.shared.publish(file_publication(self.mod, self.store, {
            "a.py": {"source_hash": "h", "artifact": {}},
            "b.py": {"source_hash": "h2", "artifact": {}},
        }))
        self.store.get_record("a.py")
        self.assertEqual(self.store.record_reads, 1)
        # Manifest reads never count as record I/O.
        self.store.paths_with_hashes()
        self.assertEqual(self.store.record_reads, 1)

    def test_digest_renderer_separates_values_that_differ_only_by_type(self):
        """The row digest decides whether an owner's rows are rewritten. A
        renderer without type tags would hash ``True`` and ``"True"``
        identically and silently keep the stale JSON attributes."""
        render = self.mod._render_for_digest
        self.assertNotEqual(render({"a": True}), render({"a": "True"}))
        self.assertNotEqual(render({"a": 1}), render({"a": "1"}))
        self.assertNotEqual(render({"a": None}), render({"a": "None"}))
        # Order-independent: the same mapping renders identically.
        self.assertEqual(render({"a": 1, "b": 2}), render({"b": 2, "a": 1}))

    def test_unpublished_generation_is_never_trusted_as_a_fingerprint(self):
        """`graph_rows_state` is written by the transaction that writes the
        rows. Without the gate a fingerprint left behind by an attempt that
        never committed its rows would read as a published generation."""
        published = self.mod.graph_published_fingerprint(
            {"graph_rows_state": "published", "payload_fingerprint": "fp"})
        self.assertEqual(published, "fp")
        for meta in (
            {"payload_fingerprint": "fp"},
            {"graph_rows_state": "pending", "payload_fingerprint": "fp"},
            {"graph_rows_state": "published"},
        ):
            self.assertEqual(self.mod.graph_published_fingerprint(meta), "")

    def test_read_state_builder_version_probe(self):
        index_dir = Path(self.tmp.name) / "idx2"
        graph_dir = index_dir / "graph"
        graph_dir.mkdir(parents=True)
        # Nothing present: unknown.
        self.assertEqual(self.mod.read_state_builder_version(index_dir), "")
        # Legacy monolithic fallback for pre-upgrade repositories.
        (graph_dir / "project-graph-state.json").write_text(
            json.dumps({"builder_version": "7"}), encoding="utf-8"
        )
        self.assertEqual(self.mod.read_state_builder_version(index_dir), "7")
        # The resident copy in the shared database takes precedence, and it is
        # the CURRENT filename that carries it (wave 1xny6).
        shared = _SharedStore(self.mod, index_dir)
        self.addCleanup(shared.close)
        shared.publish(file_publication(self.mod, shared.store, {}))
        self.assertTrue(index_paths.index_database_path(index_dir).is_file())
        (graph_dir / "project-graph-state.json").write_text(
            json.dumps({"builder_version": "stale-retired-artifact"}), encoding="utf-8"
        )
        # An EMPTY return on a healthy post-cutover store is a failure, not a
        # fail-safe: the version-staleness rebuild would silently stop firing.
        self.assertNotEqual(self.mod.read_state_builder_version(index_dir), "")
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
        return load_index_state_store().state_store_path(self.driver.index_dir)

    def _legacy_path(self) -> Path:
        return self.driver.index_dir / "graph" / "project-graph-state.json"

    def _poke_graph_meta(self, key: str, value: str) -> None:
        iss = load_index_state_store()
        store = iss.IndexStateStore(self.driver.index_dir)
        try:
            with store._conn:
                store._conn.execute(
                    "UPDATE meta SET value=? WHERE key=?",
                    (value, load_graph_indexer().GRAPH_META_PREFIX + key),
                )
        finally:
            store.close()

    def test_builder_version_mismatch_forces_full_reextract(self):
        self.driver.write("a.py", "def alpha():\n    return 1\n")
        self.driver.write("b.py", "def run():\n    alpha()\n")
        first = self.driver.build_incremental(set(self.driver.files))
        self.assertTrue(first.get("nodes"))
        # Poke an older builder_version into the graph meta namespace.
        self._poke_graph_meta("builder_version", "0")
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
        self.assertTrue(self._store_path().exists(), "shared index database must be seeded")
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
    """One publication transaction means one crash window (wave 1xny6).

    Before this wave the graph published in three steps -- store commit,
    payload file write, binding stat commit -- and each gap had its own
    recovery. The rows, the merge fragments and the published fingerprint now
    commit together with the semantic rows, so there is exactly one window:
    either the transaction committed or it did not. The derived artifacts are
    written afterwards and cannot un-publish anything.
    """

    def _seed(self):
        self.driver.write("pkg_a/definer.py", "def helper():\n    return 1\n")
        self.driver.write("pkg_a/caller.py", "def run():\n    helper()\n")
        return self.driver.build_incremental(set(self.driver.files))

    def _graph_state(self):
        iss = load_index_state_store()
        conn = iss.open_read_only(self.driver.index_dir)
        try:
            return {
                "files": dict(conn.execute("SELECT path, source_hash FROM graph_file_state")),
                "nodes": conn.execute("SELECT COUNT(*) FROM graph_nodes").fetchone()[0],
                "edges": conn.execute("SELECT COUNT(*) FROM graph_edges").fetchone()[0],
                "fingerprint": (conn.execute(
                    "SELECT value FROM meta WHERE key=?",
                    (self.mod.GRAPH_META_PREFIX + "payload_fingerprint",),
                ).fetchone() or [""])[0],
            }
        finally:
            conn.close()

    def test_abort_inside_publication_transaction_rolls_back_cleanly(self):
        """An injected fault mid-apply aborts the whole transaction: graph
        rows, extraction state and the published fingerprint all stay at the
        previous generation, and the next build recovers."""
        self._seed()
        before = self._graph_state()

        self.driver.write("pkg_a/definer.py", "def helper():\n    return 2\n")
        original = self.mod.GraphPublication.apply
        calls = {"n": 0}

        def _boom(pub_self, conn):
            calls["n"] += 1
            original(pub_self, conn)
            raise RuntimeError("injected mid-transaction fault")

        self.mod.GraphPublication.apply = _boom
        try:
            with self.assertRaises(RuntimeError):
                self.driver.build_incremental({"pkg_a/definer.py"})
        finally:
            self.mod.GraphPublication.apply = original
        self.assertEqual(calls["n"], 1)
        self.assertEqual(self._graph_state(), before,
                         "a failed attempt must publish nothing at all")

        payload = self.driver.build_incremental({"pkg_a/definer.py"})
        self.assert_equivalent(payload, self.driver.build_oracle(), "after rollback recovery")

    def test_source_change_under_prepared_rows_refuses_to_publish(self):
        """The in-transaction recheck is (size, mtime_ns) only -- no hashing
        under the write lock -- and a file that moved between preparation and
        the lock aborts the attempt instead of publishing rows that disagree
        with disk."""
        self._seed()
        before = self._graph_state()
        self.driver.write("pkg_a/definer.py", "def helper():\n    return 5\n")

        original = self.mod.GraphPublication.recheck_sources
        target = self.root / "pkg_a" / "definer.py"

        def _mutate(pub_self):
            target.write_text("def helper():\n    return 55555\n", encoding="utf-8")
            os.utime(target, ns=(0, 0))
            return original(pub_self)

        self.mod.GraphPublication.recheck_sources = _mutate
        try:
            with self.assertRaises(self.mod.GraphSourceChanged):
                self.driver.build_incremental({"pkg_a/definer.py"})
        finally:
            self.mod.GraphPublication.recheck_sources = original
        self.assertEqual(self._graph_state(), before,
                         "a moved source must abort the attempt, not publish it")

    def test_no_derived_artifact_is_written_and_none_is_needed(self):
        """Wave 1xny6 lane L6b retired the derived artifact and its writer.

        The pre-change pair here injected a write failure and then deleted the
        file out of band, proving neither forced a full re-merge. There is now
        no file at all: the build must write none, must not create the retired
        folder, and the next build must still take the zero-change fast path
        rather than the recovery the old three-step publish owed.
        """
        self._seed()
        self.driver.write("pkg_a/definer.py", "def helper():\n    return 3\n")
        with patch.object(self.mod, "_write_json",
                          side_effect=AssertionError("a derived graph artifact was written")):
            self.driver.build_incremental({"pkg_a/definer.py"})
        self.assertFalse((self.driver.index_dir / "graph").exists(),
                         "the build recreated the retired graph folder")

        after = self._graph_state()
        self.assertEqual(after["files"]["pkg_a/definer.py"],
                         self.driver._meta()["pkg_a/definer.py"]["hash"],
                         "the committed rows are the published graph")

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            payload = self.driver.build_incremental(set())
        self.assertNotIn("full re-merge", stderr.getvalue())
        self.assertEqual((payload.get("merge_stats") or {}).get("mode"), "zero-change")
        self.assert_equivalent(payload, self.driver.build_oracle(), "with no derived artifact")


# ---------------------------------------------------------------------------
# Zero-change fast path + O(changed) state I/O (AC-1)
# ---------------------------------------------------------------------------


class DeltaCostTests(_IncrementalMergeBase):
    def _graph_row_census(self) -> dict:
        iss = load_index_state_store()
        conn = iss.open_read_only(self.driver.index_dir)
        try:
            return {
                table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in load_graph_store().GRAPH_TABLES
            }
        finally:
            conn.close()

    def _graph_rows_by_owner(self) -> dict:
        """(nodes, edges, fragment bytes, rows digest) per owning file."""
        iss = load_index_state_store()
        conn = iss.open_read_only(self.driver.index_dir)
        try:
            out: dict = {}
            for owner, count in conn.execute(
                "SELECT source_file, COUNT(*) FROM graph_nodes GROUP BY source_file"
            ):
                out.setdefault(str(owner), {})["nodes"] = count
            for owner, count in conn.execute(
                "SELECT source_file, COUNT(*) FROM graph_edges GROUP BY source_file"
            ):
                out.setdefault(str(owner), {})["edges"] = count
            for path, name, fragment in conn.execute(
                "SELECT path, name, fragment FROM graph_merge_state"
            ):
                out.setdefault(str(path), {})[str(name)] = bytes(fragment)
            return out
        finally:
            conn.close()

    def test_zero_change_build_rewrites_nothing(self):
        self.driver.write("a.py", "def alpha():\n    return 1\n")
        self.driver.write("b.py", "def run():\n    alpha()\n")
        self.driver.build_incremental(set(self.driver.files))
        retired = self.driver.index_dir / "graph"
        rows_before = self._graph_row_census()

        payload = self.driver.build_incremental(set())
        stats = payload.get("merge_stats") or {}
        self.assertEqual(stats.get("mode"), "zero-change")
        self.assertEqual(stats.get("state_reads"), 0)
        self.assertEqual(stats.get("state_writes"), 0)
        self.assertEqual(stats.get("blob_writes"), 0, "zero-change must not rewrite a fragment")
        self.assertEqual(stats.get("blob_bytes"), 0)
        self.assertFalse(
            retired.exists(),
            "zero-change build recreated the retired graph folder",
        )
        self.assertEqual(self._graph_row_census(), rows_before)

    def test_one_file_edit_touches_only_changed_rows(self):
        for k in range(6):
            self.driver.write(f"pkg_a/mod_{k}.py", f"def fn_{k}():\n    return {k}\n")
        self.driver.build_incremental(set(self.driver.files))

        # A change that MOVES the graph (a new symbol), so the changed file's
        # fragment and rows genuinely differ from the published ones.
        self.driver.write("pkg_a/mod_3.py", "def fn_3():\n    return 33\n\n\ndef fn_3_extra():\n    return 3\n")
        payload = self.driver.build_incremental({"pkg_a/mod_3.py"})
        stats = payload.get("merge_stats") or {}
        self.assertEqual(stats.get("mode"), "incremental")
        self.assertEqual(stats.get("state_reads"), 0, "no unchanged row may be read")
        self.assertEqual(stats.get("state_writes"), 1, "exactly the changed row is written")
        self.assertEqual(stats.get("files_changed"), 1)
        # The merge state is PER FILE now (wave 1xny6). Every fragment is READ
        # to assemble the whole graph -- that is inherent to producing a whole
        # payload -- but only the changed file's fragment is WRITTEN BACK. The
        # counters keep both terms visible: the read is O(corpus), the write
        # is O(changed). Before this wave the write was a single O(graph) blob.
        self.assertEqual(stats.get("blob_reads"), 6, "every fragment is read to assemble")
        self.assertEqual(stats.get("blob_writes"), 1, "only the changed fragment is written")
        self.assertGreater(stats.get("blob_bytes"), 0, "fragment bytes must be visible")
        self.assert_equivalent(payload, self.driver.build_oracle(), "one-file edit")

    def test_content_only_edit_reuses_compatible_graph_work(self):
        """A change that leaves the node/edge set alone must not rewrite the
        file's graph rows or its merge fragment at all (AC-4 reuse)."""
        for k in range(6):
            self.driver.write(f"pkg_a/mod_{k}.py", f"def fn_{k}():\n    return {k}\n")
        self.driver.build_incremental(set(self.driver.files))
        before = self._graph_rows_by_owner()

        self.driver.write("pkg_a/mod_3.py", "def fn_3():\n    return 33  # same symbols\n")
        payload = self.driver.build_incremental({"pkg_a/mod_3.py"})
        stats = payload.get("merge_stats") or {}
        self.assertEqual(stats.get("blob_writes"), 0,
                         "an unchanged fragment must not be rewritten")
        self.assertEqual(self._graph_rows_by_owner(), before,
                         "compatible graph work must be reused wholesale")
        self.assert_equivalent(payload, self.driver.build_oracle(), "content-only edit")

    def test_bounded_rows_oracle_one_file_edit_unchanged_callers(self):
        """AC-4 oracle: after a one-file edit whose callers are unchanged, the
        rows written to the graph tables are bounded by that file's own nodes
        and edges plus the affected community members, and every unrelated
        file's merge-state row is untouched."""
        for k in range(8):
            self.driver.write(f"pkg_a/mod_{k}.py", f"def fn_{k}():\n    return {k}\n")
        self.driver.write(
            "pkg_a/caller.py",
            "".join(f"def call_{k}():\n    return fn_{k}()\n\n\n" for k in range(8)),
        )
        self.driver.build_incremental(set(self.driver.files))
        before = self._graph_rows_by_owner()

        edited = "pkg_a/mod_3.py"
        self.driver.write(edited, "def fn_3():\n    return 33\n\n\ndef fn_3_helper():\n    return 3\n")
        captured = {}
        original = self.mod.GraphPublication.apply

        def _capture(pub_self, conn):
            captured["nodes"] = {o: len(r) for o, r in pub_self.node_rows.items()}
            captured["edges"] = {o: len(r) for o, r in pub_self.edge_rows.items()}
            captured["fragments"] = sorted(pub_self.fragment_puts)
            captured["files"] = sorted(pub_self.file_puts)
            captured["owner_deletes"] = sorted(pub_self.owner_deletes)
            return original(pub_self, conn)

        self.mod.GraphPublication.apply = _capture
        try:
            payload = self.driver.build_incremental({edited})
        finally:
            self.mod.GraphPublication.apply = original

        self.assertEqual(captured["files"], [edited], "only the edited file's state is written")
        self.assertEqual(captured["fragments"], [edited],
                         "unrelated files' merge-state rows are untouched")
        self.assertEqual(captured["owner_deletes"], [], "nothing is retired by an edit")
        # The rows written belong to the edited file (and possibly the
        # unowned external/synthetic bucket) -- never to an unchanged caller.
        written_owners = set(captured["nodes"]) | set(captured["edges"])
        self.assertTrue(
            written_owners <= {edited, ""},
            f"rows written outside the edited file's bounds: {sorted(written_owners)}",
        )
        edited_nodes = sum(1 for n in payload["nodes"] if n.get("source_file") == edited)
        self.assertLessEqual(captured["nodes"].get(edited, 0), edited_nodes + 1)

        after = self._graph_rows_by_owner()
        untouched = set(before) - written_owners - {edited}
        self.assertTrue(untouched, "the fixture must contain unrelated owners")
        for owner in untouched:
            self.assertEqual(after.get(owner), before.get(owner),
                             f"unrelated owner rewritten: {owner}")
        self.assert_equivalent(payload, self.driver.build_oracle(), "bounded-rows oracle")

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
        # The PERSISTED payload must NOT carry merge stats. Wave 1xny6 lane
        # L6b retired the derived JSON artifact, so the persisted payload is
        # the one rebuilt from the published rows and their header.
        published = self.mod.read_published_graph_snapshot(self.root, "project")
        self.assertIsNotNone(published, "the incremental build must have published rows")
        self.assertNotIn("merge_stats", published["payload"])


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
        # This class drives the no-connection (file) mode, so the artifact it
        # just wrote is what it must read back. Wave 1xny6 moved the PUBLIC
        # `read_cluster_payload` onto the published community rows.
        payload = self.gc._legacy_file_cluster_payload(self.root, "project")
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
            r" \| sidecar: reads=\d+ writes=\d+ bytes=\d+"
            r" \| dangling: dropped=\d+"
            r" \| calls: non_callable=\d+ callable_wins=\d+ malformed_dropped=\d+",
        )


class DanglingEndpointFilterTests(_IncrementalMergeBase):
    """Wave 1x6ti (1x5pc): every served edge's endpoints are a node, an
    ``external::`` id, or a current path of the build.

    The reverse-invalidation prune drops an edge into a removed endpoint for
    exactly one build; the persisted per-file fragment keeps the edge and the
    next unrelated merge re-emits it with no target node (RED-RV2-1 on the
    deleted-doc variant, ARCH-RV3-1 on the shadowed-doc rename variant). The
    assembly-time filter drops such edges before the zero-edge doc prune so
    a doc whose only link was the deleted target is pruned exactly as a
    from-scratch build prunes it. Current-path endpoints WITHOUT a node (a
    link to a `.gitignore`, to a scan-excluded doc, a memory target into
    `docs/waves/`) are evidence the graph carries today on both sides of the
    differential, so their survival is pinned absolutely on both payloads.
    """

    _APP_V1 = "def app():\n    return 1\n"
    _APP_V2 = "def app():\n    return 2\n"

    def _seed_linked_docs(self) -> None:
        d = self.driver
        d.write("src/app.py", self._APP_V1)
        d.write("docs/target.md", "## Target\n\nSome target text here.\n")
        d.write("docs/linker.md", "## Linker\n\nSee [target](target.md) and [app](../src/app.py).\n")
        d.write("docs/only.md", "## Only\n\nJust [target](target.md).\n")

    @staticmethod
    def _edges_into(payload, target: str):
        return [e for e in payload.get("edges", []) if str(e.get("target") or "") == target]

    @staticmethod
    def _node_ids(payload) -> set[str]:
        return {str(n.get("id") or "") for n in payload.get("nodes", [])}

    def test_deleted_linked_doc_serves_no_edge_into_the_deleted_path(self):
        """AC-1 / AC-2 (RED-RV2-1): link, delete the target, build, unrelated
        edit, build -- no edge into the deleted path, and the payload equals a
        from-scratch build's, including the prune of the doc whose ONLY link
        was the deleted target."""
        d = self.driver
        self._seed_linked_docs()
        first = d.build_incremental(set(d.files))
        self.assertEqual(
            len(self._edges_into(first, "docs/target.md")), 2,
            "fixture must carry both links into the target before deletion",
        )
        d.delete("docs/target.md")
        after_delete = d.build_incremental(set(), removed={"docs/target.md"})
        self.assertEqual(self._edges_into(after_delete, "docs/target.md"), [])
        d.write("src/app.py", self._APP_V2)
        after_unrelated = d.build_incremental({"src/app.py"})
        self.assertEqual(
            self._edges_into(after_unrelated, "docs/target.md"), [],
            "the linking fragments must not re-emit the edge into the deleted doc",
        )
        self.assertNotIn(
            "docs/only.md", self._node_ids(after_unrelated),
            "a doc whose only link was the deleted target is a zero-edge doc and is pruned",
        )
        self.assert_equivalent(after_unrelated, d.build_oracle(), "after unrelated edit")

    def test_link_into_a_node_less_file_under_an_unreadable_directory_survives_the_outage(self):
        """Delivery review CODE-DEL-1: a doc link to a file the graph never
        nodes (a `.gitignore`) inside a walk-shadowed subtree has no store row
        to widen from; the 1x54z posture serves the subtree as of the last
        readable build, so the edge must survive the outage build and the
        zero-change recovery exactly as it did before the filter existed."""
        d = self.driver
        d.write("src/app.py", self._APP_V1)
        d.write("vault/a.py", "def vault_a():\n    return 1\n")
        d.write("vault/.gitignore", "*.tmp\n")
        d.write("docs/gi.md", "## GI\n\nSee [ignore](../vault/.gitignore) and [a](../vault/a.py).\n")
        first = d.build_incremental(set(d.files))
        self.assertEqual(
            [e["source"] for e in self._edges_into(first, "vault/.gitignore")], ["docs/gi.md"],
            "fixture must carry the node-less link before the outage",
        )
        self.assertNotIn("vault/.gitignore", self._node_ids(first), "the target stays node-less")
        d.write("src/app.py", self._APP_V2)
        outage = d.build_incremental({"src/app.py"}, unreadable_dirs={"vault"})
        self.assertEqual(
            [e["source"] for e in self._edges_into(outage, "vault/.gitignore")], ["docs/gi.md"],
            "the outage build keeps the link into the shadowed node-less file",
        )
        self.assertEqual(outage["merge_stats"].get("edges_dropped_dangling"), 0)
        self.assertIn("vault/a.py::vault_a", self._node_ids(outage), "the shadowed subtree is kept")
        recovered = d.build_incremental(set())
        self.assertEqual(
            [e["source"] for e in self._edges_into(recovered, "vault/.gitignore")], ["docs/gi.md"],
            "the zero-change recovery still serves the link",
        )
        self.assert_equivalent(recovered, d.build_oracle(), "after recovery")

    def test_unrelated_outage_drops_stale_edges_and_respects_the_directory_boundary(self):
        """Delivery review CODE-RV1-1 / QA-RV1-2: the unreadable-directory
        exemption is local to endpoints under the reported directory. Two
        deletions merged on a readable build leave stale fragments; an
        unrelated outage (`vault` unreadable, while the stale targets live in
        `docs/` and in the sibling `vault2/`) must still drop both re-emitted
        edges: an over-broad exemption or a boundary-less prefix match keeps
        them."""
        d = self.driver
        d.write("src/app.py", self._APP_V1)
        d.write("vault/a.py", "def vault_a():\n    return 1\n")
        d.write("vault2/gone.md", "## Gone\n\nSibling directory doc.\n")
        d.write("docs/x.md", "## X\n\nSee [gone](../vault2/gone.md).\n")
        d.write("docs/target.md", "## Target\n\nText.\n")
        d.write("docs/linker.md", "## Linker\n\nSee [target](target.md).\n")
        first = d.build_incremental(set(d.files))
        self.assertEqual(len(self._edges_into(first, "vault2/gone.md")), 1)
        self.assertEqual(len(self._edges_into(first, "docs/target.md")), 1)
        d.delete("vault2/gone.md")
        d.delete("docs/target.md")
        pruned = d.build_incremental(set(), removed={"vault2/gone.md", "docs/target.md"})
        self.assertEqual(self._edges_into(pruned, "vault2/gone.md"), [])
        self.assertEqual(self._edges_into(pruned, "docs/target.md"), [])
        d.write("src/app.py", self._APP_V2)
        outage = d.build_incremental({"src/app.py"}, unreadable_dirs={"vault"})
        self.assertEqual(outage["merge_stats"].get("files_shadowed"), 1, "non-vacuity: the outage shadowed vault/a.py")
        self.assertEqual(self._edges_into(outage, "vault2/gone.md"), [], "a sibling directory is not under the unreadable one")
        self.assertEqual(self._edges_into(outage, "docs/target.md"), [], "an unrelated outage exempts nothing outside the directory")
        self.assertEqual(outage["merge_stats"].get("edges_dropped_dangling"), 2)
        self.assertIn("vault/a.py::vault_a", self._node_ids(outage))
        # The boundary itself: a stale link into a node-less file under the
        # SIBLING directory that the last published payload still serves
        # (its delete-only build has no store row to merge and takes the
        # zero-change fast path), so only the directory boundary decides.
        d.write("vault2/.gitignore", "*.tmp\n")
        d.write("docs/y.md", "## Y\n\nSee [ignore](../vault2/.gitignore).\n")
        served = d.build_incremental({"vault2/.gitignore", "docs/y.md"})
        self.assertEqual(len(self._edges_into(served, "vault2/.gitignore")), 1)
        d.delete("vault2/.gitignore")
        fast = d.build_incremental(set(), removed={"vault2/.gitignore"})
        self.assertEqual(
            len(self._edges_into(fast, "vault2/.gitignore")), 1,
            "non-vacuity: the delete-only build of a node-less file takes the fast path and still serves the link",
        )
        d.write("src/app.py", self._APP_V1)
        outage2 = d.build_incremental({"src/app.py"}, unreadable_dirs={"vault"})
        self.assertEqual(
            self._edges_into(outage2, "vault2/.gitignore"), [],
            "vault2 is not under vault: the last-served stale link is dropped at the boundary",
        )
        # Three drops: the two stale fragments from the earlier deletions
        # re-emit on every merge (dropped again), plus the sibling link.
        self.assertEqual(outage2["merge_stats"].get("edges_dropped_dangling"), 3)

    def test_outage_does_not_resurrect_an_edge_the_last_readable_build_dropped(self):
        """Delivery review CODE-RV1-2 / QA-RV1-1: the exemption serves the
        shadowed subtree AS OF THE LAST READABLE BUILD. A doc under `vault`
        is deleted and the deletion merged (edge dropped, its only-link doc
        pruned); the outage build must not resurrect the edge or the node
        from the stale fragments, the zero-change recovery must not either,
        and the next readable real-work build equals the oracle."""
        d = self.driver
        d.write("src/app.py", self._APP_V1)
        d.write("vault/a.py", "def vault_a():\n    return 1\n")
        d.write("vault/v.md", "## V\n\nA doc inside the vault.\n")
        d.write("docs/gi.md", "## GI\n\nSee [v](../vault/v.md) and [a](../vault/a.py).\n")
        d.write("docs/onlyv.md", "## Only\n\nJust [v](../vault/v.md).\n")
        first = d.build_incremental(set(d.files))
        self.assertEqual(len(self._edges_into(first, "vault/v.md")), 2, "fixture must carry both links")
        d.delete("vault/v.md")
        merged = d.build_incremental(set(), removed={"vault/v.md"})
        self.assertEqual(self._edges_into(merged, "vault/v.md"), [])
        self.assertNotIn("docs/onlyv.md", self._node_ids(merged), "the only-link doc is pruned on the readable build")
        d.write("src/app.py", self._APP_V2)
        outage = d.build_incremental({"src/app.py"}, unreadable_dirs={"vault"})
        self.assertEqual(
            self._edges_into(outage, "vault/v.md"), [],
            "the outage must not resurrect an edge the last readable build dropped",
        )
        self.assertNotIn("docs/onlyv.md", self._node_ids(outage))
        self.assertEqual(outage["merge_stats"].get("edges_dropped_dangling"), 2)
        self.assertIn("vault/a.py::vault_a", self._node_ids(outage), "the shadowed subtree itself is kept")
        recovered = d.build_incremental(set())
        self.assertEqual(self._edges_into(recovered, "vault/v.md"), [])
        d.write("src/other.py", "def other():\n    return 3\n")
        after = d.build_incremental({"src/other.py"})
        self.assert_equivalent(after, d.build_oracle(), "readable real-work build after the outage")

    def test_dropped_dangling_edges_are_counted_in_merge_stats(self):
        """AC-5: the filter reports what it dropped; zero when nothing dangled."""
        d = self.driver
        self._seed_linked_docs()
        first = d.build_incremental(set(d.files))
        self.assertEqual(first["merge_stats"].get("edges_dropped_dangling"), 0)
        d.delete("docs/target.md")
        after_delete = d.build_incremental(set(), removed={"docs/target.md"})
        # The reverse-invalidation prune already removed this build's edges.
        self.assertEqual(after_delete["merge_stats"].get("edges_dropped_dangling"), 0)
        d.write("src/app.py", self._APP_V2)
        after_unrelated = d.build_incremental({"src/app.py"})
        self.assertEqual(
            after_unrelated["merge_stats"].get("edges_dropped_dangling"), 2,
            "both re-emitted fragment edges into the deleted doc are dropped and counted",
        )

    def test_shadowed_doc_rename_serves_no_edge_to_the_removed_symbol(self):
        """AC-3 (ARCH-RV3-1): a symbol a shadowed doc mentions is renamed
        during a walk outage; after recovery and an unrelated edit the payload
        carries no edge to the removed symbol id and equals a from-scratch
        build's."""
        d = self.driver
        d.write("src/app.py", "def frobnicate_widget():\n    return 1\n")
        d.write("vault/notes.md", "## Vault\n\nUses `frobnicate_widget` from the app.\n")
        d.write("vault/a.py", "def vault_a():\n    return 1\n")
        first = d.build_incremental(set(d.files))
        self.assertEqual(
            [
                e["source"]
                for e in self._edges_into(first, "src/app.py::frobnicate_widget")
                if e.get("relation") == "doc_references_code"
            ],
            ["vault/notes.md"],
            "fixture must carry the doc mention edge before the rename",
        )
        d.write("src/app.py", "def frobnicate_widget_v2():\n    return 1\n")
        outage = d.build_incremental({"src/app.py"}, unreadable_dirs={"vault"})
        self.assertIn("vault/a.py::vault_a", self._node_ids(outage), "the shadowed subtree is kept")
        self.assertEqual(self._edges_into(outage, "src/app.py::frobnicate_widget"), [])
        recovered = d.build_incremental(set())
        self.assertEqual(self._edges_into(recovered, "src/app.py::frobnicate_widget"), [])
        d.write("src/other.py", "def other():\n    return 3\n")
        after_unrelated = d.build_incremental({"src/other.py"})
        self.assertEqual(
            self._edges_into(after_unrelated, "src/app.py::frobnicate_widget"), [],
            "the preserved fragment must not re-emit its edge to the removed symbol",
        )
        self.assert_equivalent(after_unrelated, d.build_oracle(), "after recovery and unrelated edit")

    def test_external_and_node_less_current_path_endpoints_survive(self):
        """AC-4: `external::` endpoints (an external supertype on `extends` and
        `implements`, an unresolved call) and node-less current-path endpoints
        (a link to `.gitignore`, a link to a scan-excluded doc, a memory
        target into `docs/waves/`) survive the filter -- pinned as ABSOLUTE
        presence assertions on BOTH payloads, because the differential is
        blind to an exemption the oracle applies too."""
        d = self.driver
        d.write(
            "com/x/Repo.java",
            "package com.x;\nimport org.ext.BaseRepo;\n"
            "public class Repo extends BaseRepo implements Runnable {\n"
            "  public void run() { helper(); }\n}\n",
        )
        d.write(".gitignore", "*.pyc\n")
        d.write("docs/waves/w.md", "## Wave\n\nexcluded from the doc scan.\n")
        d.write("docs/gi.md", "## GI\n\nSee [ignore](../.gitignore) and [wave](waves/w.md).\n")
        d.write(
            "docs/agents/memory/mem-1.md",
            "# Mem\n\n## Targets\n\n- `docs/waves/w.md`\n\n## Body\n\ntext\n",
        )
        incremental = d.build_incremental(set(d.files))
        # An unrelated edit so the served payload is a re-emission of stored
        # fragments, the path on which the filter runs against a stale map.
        d.write("src/late.py", "def late():\n    return 0\n")
        incremental = d.build_incremental({"src/late.py"})
        oracle = d.build_oracle()
        expected = {
            ("com/x/Repo.java", "external::BaseRepo", "extends"),
            ("com/x/Repo.java", "external::Runnable", "implements"),
            ("com/x/Repo.java::Repo.run", "external::Repo.helper", "calls"),
            ("docs/gi.md", ".gitignore", "doc_references_doc"),
            ("docs/gi.md", "docs/waves/w.md", "doc_references_doc"),
            ("docs/agents/memory/mem-1.md", "docs/waves/w.md", "memory_targets"),
        }
        for label, payload in (("incremental", incremental), ("oracle", oracle)):
            ids = self._node_ids(payload)
            keys = {
                (str(e.get("source") or ""), str(e.get("target") or ""), str(e.get("relation") or ""))
                for e in payload.get("edges", [])
            }
            self.assertTrue(
                expected <= keys,
                f"[{label}] missing exempt endpoint edges: {sorted(expected - keys)}",
            )
            for tgt in (".gitignore", "docs/waves/w.md"):
                self.assertNotIn(tgt, ids, f"[{label}] {tgt} must stay node-less (the exemption is what keeps its edge)")
        self.assert_equivalent(incremental, oracle, "exempt endpoints")


class LaterCreatedDocTargetTests(_IncrementalMergeBase):
    DOC = "docs/linker.md"

    def _poke_graph_meta(self, index_dir, key: str, value: str) -> None:
        iss = load_index_state_store()
        state = iss.IndexStateStore(index_dir)
        try:
            with state._conn:
                state._conn.execute(
                    "UPDATE meta SET value=? WHERE key=?",
                    (value, self.mod.GRAPH_META_PREFIX + key),
                )
        finally:
            state.close()

    def _stored_unresolved(self):
        # A new connection after each build proves both representations survive
        # session close, including a document pruned from the served graph.
        shared = _SharedStore(self.mod, self.driver.index_dir)
        try:
            artifact = shared.store.get_record(self.DOC)["artifact"]
            summary = shared.store.read_merge_state()["files"][self.DOC]
            return artifact.get("unresolved_doc_targets", []), summary.get("unresolved_doc_targets", [])
        finally:
            shared.close()

    def _assert_link(self, payload, target, *, noded):
        ids = {n["id"] for n in payload["nodes"]}
        self.assertIn(self.DOC, ids)
        self.assertEqual(target in ids, noded)
        self.assertIn((self.DOC, target, "doc_references_doc", "EXTRACTED"), _edge_keys(payload))
        self.assert_equivalent(payload, self.driver.build_oracle())

    def test_target_only_creation_then_unchanged_and_unrelated(self):
        from unittest.mock import patch
        for target, body, reference, noded in (
            ("src/later.py", "def later():\n    return 1\n", "[later](../src/later.py#part)", True),
            ("assets/.gitignore", "cache/\n", "`/assets/.gitignore`", False),
        ):
            with self.subTest(target=target):
                self.driver = _RepoDriver(self.mod, self.root / str(noded))
                d = self.driver
                d.write(self.DOC, reference + "\n")
                first = d.build_incremental({self.DOC})
                self.assertNotIn(self.DOC, {n["id"] for n in first["nodes"]})
                self.assertEqual(self._stored_unresolved(), ([target], [target]))
                d.write("other.py", "VALUE = 1\n")
                with patch.object(self.mod.GraphIndexSession, "_extract_doc_artifact", autospec=True,
                                  side_effect=self.mod.GraphIndexSession._extract_doc_artifact) as scan:
                    d.build_incremental({"other.py"})
                    idle = d.build_incremental(set())
                self.assertEqual(scan.call_count, 0, "absent targets never trigger rescans")
                self.assertEqual(self._stored_unresolved(), ([target], [target]))
                self.assertEqual(idle["merge_stats"]["state_reads"], 0)
                self.assertEqual(idle["merge_stats"]["state_writes"], 0)
                self.assertEqual(idle["merge_stats"]["blob_writes"], 0)
                d.write(target, body)
                with patch.object(self.mod.GraphIndexSession, "_extract_doc_artifact", autospec=True,
                                  side_effect=self.mod.GraphIndexSession._extract_doc_artifact) as scan:
                    created = d.build_incremental({target})
                self.assertEqual(scan.call_count, 1)
                self._assert_link(created, target, noded=noded)
                self.assertEqual(self._stored_unresolved(), ([], []))
                with patch.object(self.mod.GraphIndexSession, "_extract_doc_artifact", autospec=True,
                                  side_effect=self.mod.GraphIndexSession._extract_doc_artifact) as scan:
                    unchanged = d.build_incremental(set())
                self.assertEqual(scan.call_count, 0)
                self._assert_link(unchanged, target, noded=noded)
                with patch.object(self.mod.GraphIndexSession, "_extract_doc_artifact", autospec=True,
                                  side_effect=self.mod.GraphIndexSession._extract_doc_artifact) as scan:
                    d.write("other.py", "VALUE = 2\n")
                    unrelated = d.build_incremental({"other.py"})
                self.assertEqual(scan.call_count, 0, "resolved targets stop repair rescans")
                self._assert_link(unrelated, target, noded=noded)

    def test_failed_or_unreadable_doc_retries_on_unchanged_recovery(self):
        from unittest.mock import patch
        for failure in ("read", "exists", "directory"):
            with self.subTest(failure=failure):
                self.driver = _RepoDriver(self.mod, self.root / failure)
                d = self.driver
                target = "assets/.gitignore"
                d.write(self.DOC, "[later](/assets/.gitignore)\n")
                d.build_incremental({self.DOC})
                d.write(target, "cache/\n")
                if failure == "directory":
                    outage = d.build_incremental({target}, unreadable_dirs={"docs"})
                else:
                    original = getattr(Path, "read_text" if failure == "read" else "exists")
                    def fail_doc(path, *args, **kwargs):
                        if path == d.root / self.DOC:
                            raise PermissionError("injected unreadable document")
                        return original(path, *args, **kwargs)
                    with patch.object(Path, "read_text" if failure == "read" else "exists", fail_doc):
                        outage = d.build_incremental({target})
                self.assertNotIn(self.DOC, {n["id"] for n in outage["nodes"]})
                self.assertEqual(self._stored_unresolved(), ([target], [target]))
                recovered = d.build_incremental(set())
                self._assert_link(recovered, target, noded=False)
                self.assertEqual(self._stored_unresolved(), ([], []))

    def test_candidates_keep_existing_normalization_and_exclusions(self):
        d = self.driver
        d.write(self.DOC, """[relative](later.md#part) [root](/assets/target.txt)
[dot](./assets/dot.txt) [parent](../assets/parent.txt)
[self](linker.md) [anchor](#part) [web](https://example.com/x.md)
[mail](mailto:x@example.com) [ftp](ftp://example.com/x.md)
`/assets/backtick.txt` `not a path.md` `plainword` `https://example.com/y.md`
""")
        d.build_incremental({self.DOC})
        expected = sorted(["docs/later.md", "assets/target.txt", "assets/dot.txt",
                           "assets/parent.txt", "assets/backtick.txt"])
        self.assertEqual(self._stored_unresolved(), (expected, expected))
        for target in expected:
            d.write(target, "plain text\n")
        payload = d.build_incremental(set(expected))
        targets = {e["target"] for e in payload["edges"] if e["source"] == self.DOC
                   and e["relation"] == "doc_references_doc"}
        self.assertEqual(targets, set(expected))
        self.assert_equivalent(payload, d.build_oracle())
        self.assertEqual(self._stored_unresolved(), ([], []))

    def test_read_only_preflight_reuses_blob_and_detects_version_mismatch(self):
        from unittest.mock import patch
        d = self.driver
        target = "assets/.gitignore"
        def preflight(**kwargs):
            return self.mod.read_pending_doc_link_repairs(
                index_dir=d.index_dir, current_paths=set(d.files),
                walker_version="1", chunker_version="1", **kwargs,
            )
        self.assertIsNone(preflight())
        self.assertFalse(d.index_dir.exists(), "read-only absence probe must not create state")
        d.write(self.DOC, "[later](/assets/.gitignore)\n")
        d.build_incremental({self.DOC})
        self.assertEqual(preflight()["pending_docs"], [])
        d.write(target, "cache/\n")
        index_dir = d.index_dir
        watched = [q for q in index_dir.rglob("*") if q.is_file()]
        before = {q: (q.read_bytes(), q.stat().st_mtime_ns) for q in watched}
        with patch.object(self.mod.GraphStateStore, "__init__", side_effect=AssertionError("mutating store open")):
            plan = preflight()
            self.assertEqual(preflight(unreadable_dirs={"docs"})["pending_docs"], [])
        self.assertEqual(plan["pending_docs"], [self.DOC])
        self.assertFalse(plan["rebuild_required"])
        for q in watched:
            # SQLite read transactions touch the SHM reader-lock mapping;
            # durable database/WAL/payload contents and timestamps stay put.
            if not q.name.endswith("-shm") and not q.name.endswith(".lock"):
                self.assertEqual(before[q], (q.read_bytes(), q.stat().st_mtime_ns), q.name)
        with patch.object(self.mod.GraphStateStore, "read_merge_state",
                          side_effect=AssertionError("duplicate merge-state read")):
            payload = self.mod.update_graph_index(
                root=d.root, index_dir=d.index_dir, layer="project",
                files=[d.root / rel for rel in d.files], current_file_meta=d._meta(),
                changed=set(), removed=set(), walker_version="1", chunker_version="1",
                doc_link_repair_plan=plan,
            )
        self._assert_link(payload, target, noded=False)
        # A current-store plan cannot override the builder migration reset.
        self._poke_graph_meta(d.index_dir, "builder_version", "50")
        mismatch = preflight()
        self.assertTrue(mismatch["rebuild_required"])
        self.assertIsNone(mismatch["merge_state"])
        with patch.object(self.mod.GraphIndexSession, "_extract_doc_artifact", autospec=True,
                          side_effect=self.mod.GraphIndexSession._extract_doc_artifact) as scan:
            rebuilt = self.mod.update_graph_index(
                root=d.root, index_dir=d.index_dir, layer="project",
                files=[d.root / rel for rel in d.files], current_file_meta=d._meta(),
                changed=set(), removed=set(), walker_version="1", chunker_version="1",
                doc_link_repair_plan=mismatch,
            )
        self.assertEqual(scan.call_count, 1)
        self.assertEqual(self.mod.read_state_builder_version(d.index_dir), self.mod.GRAPH_BUILDER_VERSION)
        self._assert_link(rebuilt, target, noded=False)

    def test_full_merge_recovery_uses_retained_artifact_obligation(self):
        d = self.driver
        target = "assets/.gitignore"
        d.write(self.DOC, "[later](/assets/.gitignore)\n")
        d.build_incremental({self.DOC})
        # Interrupted-state recovery still has the source artifacts and a
        # published fingerprint, but lacks the merge fragments needed to prove
        # idleness.
        iss = load_index_state_store()
        state = iss.IndexStateStore(d.index_dir)
        try:
            with state._conn:
                state._conn.execute("DELETE FROM graph_merge_state")
        finally:
            state.close()
        d.write(target, "cache/\n")
        plan = self.mod.read_pending_doc_link_repairs(
            index_dir=d.index_dir, current_paths=set(d.files),
            walker_version="1", chunker_version="1",
        )
        self.assertTrue(plan["rebuild_required"])
        recovered = self.mod.update_graph_index(
            root=d.root, index_dir=d.index_dir, layer="project",
            files=[d.root / rel for rel in d.files], current_file_meta=d._meta(),
            changed=set(), removed=set(), walker_version="1", chunker_version="1",
            doc_link_repair_plan=plan,
        )
        self._assert_link(recovered, target, noded=False)
        self.assertEqual(self._stored_unresolved(), ([], []))


class InheritanceEdgeIncrementalTests(_IncrementalMergeBase):
    """Wave 1p9qh (1p9qa): incremental soundness for the new `extends`/
    `implements` relations and the inherited-method output pass.

    The supertype edges add new `_edge_lookup_keys` shapes (bare + final
    segment for the inheritance relations), so the differential oracle is
    extended with Java inheritance scenarios: supertype twin add/remove must
    demote/promote the extends edge in UNTOUCHED files, and the inherited-
    method bind (an output-pass recomputation) must follow supertype-chain
    edits in files the caller never touched.
    """

    _BASE = "package com.app;\npublic class AbstractRepo {\n    public void persist() {}\n}\n"
    _CHILD = "package com.app;\npublic class UserRepo extends AbstractRepo {\n    public void other() {}\n}\n"
    _SVC = (
        "package com.app;\npublic class Service {\n"
        "    void process() {\n        UserRepo repo = new UserRepo();\n        repo.persist();\n    }\n}\n"
    )

    def setUp(self):
        super().setUp()
        try:
            import tree_sitter_java  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_java not available in test env")

    def test_supertype_twin_add_demotes_untouched_extends_edge(self):
        self.driver.write("com/app/AbstractRepo.java", self._BASE)
        self.driver.write("com/app/UserRepo.java", self._CHILD)
        payload = self.driver.build_incremental(set(self.driver.files))
        bound = _find_edges(
            payload, source_prefix="com/app/UserRepo.java",
            target="com/app/AbstractRepo.java", relation="extends",
        )
        self.assertTrue(bound, "unique supertype must bind cross-file")
        self.assertEqual(bound[0]["confidence"], "RECEIVER_RESOLVED")

        # A same-name twin in a DIFFERENT package makes the candidate set
        # ambiguous; UserRepo.java is untouched. The extends edge must
        # re-resolve (scope-(b) coverage for the new inheritance lookup keys)
        # — and Java-faithfully it REBINDS to the same-package twin via the
        # declared-package tier (1p9qb: keyed on the parsed `package`
        # declaration; same package shadows the outsider), demoted to
        # heuristic EXTRACTED confidence.
        self.driver.write(
            "com/other/AbstractRepo.java",
            "package com.other;\npublic class AbstractRepo {\n    public void persist() {}\n}\n",
        )
        payload = self.driver.build_incremental({"com/other/AbstractRepo.java"})
        rebound = _find_edges(
            payload, source_prefix="com/app/UserRepo.java",
            target="com/app/AbstractRepo.java", relation="extends",
        )
        self.assertTrue(rebound, "same-package supertype must shadow the cross-package twin")
        self.assertEqual(
            rebound[0]["confidence"], "EXTRACTED",
            "heuristic same-dir rebind must demote the untouched file's edge from RECEIVER_RESOLVED",
        )
        self.assert_equivalent(payload, self.driver.build_oracle(), "after supertype twin add")

        # Deleting the twin re-promotes the untouched file's edge.
        self.driver.delete("com/other/AbstractRepo.java")
        payload = self.driver.build_incremental(set(), removed={"com/other/AbstractRepo.java"})
        bound = _find_edges(
            payload, source_prefix="com/app/UserRepo.java",
            target="com/app/AbstractRepo.java", relation="extends",
        )
        self.assertTrue(bound, "now-unique supertype must PROMOTE in the untouched file")
        self.assertEqual(bound[0]["confidence"], "RECEIVER_RESOLVED")
        self.assert_equivalent(payload, self.driver.build_oracle(), "after supertype twin delete")

    def test_cross_package_supertype_twins_demote_to_external(self):
        """Two twins, NEITHER in the subclass's own package and no import —
        the extends edge in the untouched file demotes to external:: refusal."""
        self.driver.write(
            "com/x/AbstractRepo.java",
            "package com.x;\npublic class AbstractRepo {\n    public void persist() {}\n}\n",
        )
        self.driver.write("lib/app/UserRepo.java", self._CHILD)
        payload = self.driver.build_incremental(set(self.driver.files))
        self.assertTrue(
            _find_edges(payload, source_prefix="lib/app/UserRepo.java",
                        target="com/x/AbstractRepo.java", relation="extends"),
            "unique cross-package supertype binds",
        )

        self.driver.write(
            "com/y/AbstractRepo.java",
            "package com.y;\npublic class AbstractRepo {\n    public void persist() {}\n}\n",
        )
        payload = self.driver.build_incremental({"com/y/AbstractRepo.java"})
        self.assertFalse(
            _find_edges(payload, source_prefix="lib/app/UserRepo.java",
                        target="com/x/AbstractRepo.java", relation="extends"),
            "ambiguous supertype must DEMOTE the previously-bound extends edge in the untouched file",
        )
        external = _find_edges(
            payload, source_prefix="lib/app/UserRepo.java",
            target="external::AbstractRepo", relation="extends",
        )
        self.assertTrue(external, "demoted supertype returns to external::AbstractRepo (refusal)")
        self.assertEqual(external[0]["confidence"], "EXTRACTED")
        self.assert_equivalent(payload, self.driver.build_oracle(), "after second cross-package twin")

    def test_inherited_bind_follows_supertype_edit_in_untouched_caller(self):
        """The inherited-method bind is an OUTPUT-pass product recomputed each
        build, so editing the supertype chain updates binds in files that were
        never re-extracted."""
        self.driver.write("com/app/AbstractRepo.java", self._BASE)
        self.driver.write("com/app/UserRepo.java", self._CHILD)
        self.driver.write("com/app/Service.java", self._SVC)
        payload = self.driver.build_incremental(set(self.driver.files))
        bound = _find_edges(
            payload, source_prefix="com/app/Service.java",
            target="com/app/AbstractRepo.java::AbstractRepo.persist", relation="calls",
        )
        self.assertTrue(bound, "inherited method must bind through the extends edge")
        self.assertEqual(bound[0].get("via_supertype"), ["com/app/AbstractRepo.java"])

        # Remove persist() from the supertype; Service.java untouched.
        self.driver.write(
            "com/app/AbstractRepo.java",
            "package com.app;\npublic class AbstractRepo {\n    public void other() {}\n}\n",
        )
        payload = self.driver.build_incremental({"com/app/AbstractRepo.java"})
        self.assertFalse(
            _find_edges(payload, source_prefix="com/app/Service.java",
                        target="com/app/AbstractRepo.java::AbstractRepo.persist"),
            "removing the definer must release the inherited bind in the untouched caller",
        )
        self.assertTrue(
            _find_edges(payload, source_prefix="com/app/Service.java",
                        target="external::UserRepo.persist", relation="calls"),
            "released inherited bind returns to the external receiver form",
        )
        self.assert_equivalent(payload, self.driver.build_oracle(), "after definer removal")

        # Restore the definer: the bind comes back without touching the caller.
        self.driver.write("com/app/AbstractRepo.java", self._BASE)
        payload = self.driver.build_incremental({"com/app/AbstractRepo.java"})
        self.assertTrue(
            _find_edges(payload, source_prefix="com/app/Service.java",
                        target="com/app/AbstractRepo.java::AbstractRepo.persist", relation="calls"),
            "restoring the definer must re-bind the untouched caller",
        )
        self.assert_equivalent(payload, self.driver.build_oracle(), "after definer restore")

    def test_super_call_marker_differential_equivalence(self):
        self.driver.write("com/app/AbstractRepo.java", self._BASE)
        self.driver.write(
            "com/app/UserRepo.java",
            "package com.app;\npublic class UserRepo extends AbstractRepo {\n"
            "    public void persist() { super.persist(); }\n}\n",
        )
        payload = self.driver.build_incremental(set(self.driver.files))
        self.assertTrue(
            _find_edges(payload, source_prefix="com/app/UserRepo.java",
                        target="com/app/AbstractRepo.java::AbstractRepo.persist", relation="calls"),
            "super call binds via the single extends target",
        )
        self.assert_equivalent(payload, self.driver.build_oracle(), "initial super-call build")

        # Retarget the parent: UserRepo now extends an external base; the
        # super call must return to its refusal marker, incrementally equal
        # to the oracle.
        self.driver.write(
            "com/app/UserRepo.java",
            "package com.app;\npublic class UserRepo extends ExternalBase {\n"
            "    public void persist() { super.persist(); }\n}\n",
        )
        payload = self.driver.build_incremental({"com/app/UserRepo.java"})
        self.assertTrue(
            _find_edges(payload, source_prefix="com/app/UserRepo.java",
                        target="external::super.UserRepo.persist", relation="calls"),
            "unresolvable super call keeps the explicit marker",
        )
        self.assert_equivalent(payload, self.driver.build_oracle(), "after parent retarget")

    def test_static_import_supertype_definer_flip_differential(self):
        """Wave 1p9qh adversarial fix (F1): the static-or-inherited marker is
        arbitrated in the OUTPUT pass recomputed each build, so adding or
        removing a supertype definer in a SEPARATE file must flip the bind
        of an untouched static-importing caller — JLS 6.4.1 faithfully
        (inherited definer shadows the static import) and incrementally
        equal to the full-rebuild oracle at every step."""
        maths = "package com.util;\npublic class Maths {\n    public static void helper() {}\n}\n"
        base_plain = "package com.app;\npublic class Base {\n    public void other() {}\n}\n"
        base_definer = (
            "package com.app;\npublic class Base {\n"
            "    public void other() {}\n    public void helper() {}\n}\n"
        )
        child = (
            "package com.app;\nimport static com.util.Maths.helper;\n"
            "public class Child extends Base {\n    public void run() {\n        helper();\n    }\n}\n"
        )
        self.driver.write("com/util/Maths.java", maths)
        self.driver.write("com/app/Base.java", base_plain)
        self.driver.write("com/app/Child.java", child)
        payload = self.driver.build_incremental(set(self.driver.files))
        self.assertTrue(
            _find_edges(payload, source_prefix="com/app/Child.java",
                        target="com/util/Maths.java::Maths.helper", relation="calls"),
            "no supertype definer -> the static-import claim stands (project bind)",
        )
        self.assert_equivalent(payload, self.driver.build_oracle(), "initial static-claim build")

        # Add helper() to the supertype in a SEPARATE file; Child.java untouched.
        # Inherited member now shadows the static import (JLS 6.4.1).
        self.driver.write("com/app/Base.java", base_definer)
        payload = self.driver.build_incremental({"com/app/Base.java"})
        bound = _find_edges(payload, source_prefix="com/app/Child.java",
                            target="com/app/Base.java::Base.helper", relation="calls")
        self.assertTrue(bound, "added supertype definer must shadow the static import in the untouched caller")
        self.assertEqual(bound[0].get("via_supertype"), ["com/app/Base.java"])
        self.assertFalse(
            _find_edges(payload, source_prefix="com/app/Child.java",
                        target="com/util/Maths.java::Maths.helper", relation="calls"),
            "the shadowed static bind must be released",
        )
        self.assert_equivalent(payload, self.driver.build_oracle(), "after definer add")

        # Remove the definer again: the static claim stands once more.
        self.driver.write("com/app/Base.java", base_plain)
        payload = self.driver.build_incremental({"com/app/Base.java"})
        self.assertTrue(
            _find_edges(payload, source_prefix="com/app/Child.java",
                        target="com/util/Maths.java::Maths.helper", relation="calls"),
            "removing the definer must restore the standing static claim in the untouched caller",
        )
        self.assertFalse(
            _find_edges(payload, source_prefix="com/app/Child.java",
                        target="com/app/Base.java::Base.helper", relation="calls"),
            "the released inherited bind must not linger",
        )
        self.assert_equivalent(payload, self.driver.build_oracle(), "after definer removal")


class JavaPackageKeyingIncrementalTests(_IncrementalMergeBase):
    """Wave 1p9qh (1p9qb): the declared-package keying fact is node-borne
    (`declared_package` on the file's module node), so a package-declaration
    flip in a CANDIDATE file must re-key the same-package disambiguation tier
    for untouched callers — incrementally equal to the full-rebuild oracle.

    Extends the 1p9q2 differential harness with the new keying shape: the
    twin-flip here is driven purely by a `package` statement edit (no symbol
    rename, no file add/delete), the exact delta the directory-keyed tier was
    blind to."""

    _CALLER = "package com.x;\npublic class Foo { Bar b; void run() { b.go(); } }\n"

    def setUp(self):
        super().setUp()
        try:
            import tree_sitter_java  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_java not available in test env")

    def test_candidate_package_flip_rekeys_untouched_caller(self):
        self.driver.write("a/Foo.java", self._CALLER)
        self.driver.write("b/Bar.java", "package com.x;\npublic class Bar { public void go() {} }\n")
        self.driver.write("c/Bar.java", "package com.y;\npublic class Bar { public void go() {} }\n")
        payload = self.driver.build_incremental(set(self.driver.files))
        self.assertTrue(
            _find_edges(payload, source_prefix="a/Foo.java", target="b/Bar.java::Bar.go", relation="calls"),
            "unique same-declared-package twin must bind across directories",
        )

        # Flip ONLY c/Bar.java's package declaration into com.x: two same-
        # package twins now exist, so the untouched caller's bind must demote.
        self.driver.write("c/Bar.java", "package com.x;\npublic class Bar { public void go() {} }\n")
        payload = self.driver.build_incremental({"c/Bar.java"})
        self.assertFalse(
            _find_edges(payload, source_prefix="a/Foo.java", target="b/Bar.java::Bar.go"),
            "a second same-package twin must DEMOTE the untouched caller's bind",
        )
        self.assertTrue(
            _find_edges(payload, source_prefix="a/Foo.java", target="external::Bar.go", relation="calls"),
            "demoted edge returns to external::Bar.go",
        )
        self.assert_equivalent(payload, self.driver.build_oracle(), "after package flip in")

        # Flip it back out: the untouched caller's bind must return.
        self.driver.write("c/Bar.java", "package com.y;\npublic class Bar { public void go() {} }\n")
        payload = self.driver.build_incremental({"c/Bar.java"})
        self.assertTrue(
            _find_edges(payload, source_prefix="a/Foo.java", target="b/Bar.java::Bar.go", relation="calls"),
            "removing the twin's same-package status must REBIND the untouched caller",
        )
        self.assert_equivalent(payload, self.driver.build_oracle(), "after package flip back out")


class EmbeddedSqlCaptureIncrementalTests(_IncrementalMergeBase):
    """Wave 1p9qi (1p9qf): `sql_capture_candidates` / `sql_capture_dynamic`
    must ride the per-file fragment passthrough — a cached (untouched) file's
    captures survive an incremental merge, so the finalize bind pass keeps
    re-minting its edges. Without the passthrough the bind edge silently
    vanishes on the first unrelated edit (the `config_read_candidates`
    failure class)."""

    _SCHEMA = "CREATE TABLE users (id INT PRIMARY KEY);\n"
    _DAO = (
        "public class Dao {\n"
        "  void run(java.sql.Connection conn, String t) {\n"
        "    conn.prepareStatement(\"SELECT * FROM users\");\n"
        "    conn.prepareStatement(\"SELECT * FROM \" + t);\n"
        "  }\n"
        "}\n"
    )

    def _require(self, *langs: str):
        for lang in langs:
            if getattr(self.mod, "_ts_get_parser", lambda *_: None)(lang) is None:
                self.skipTest(f"tree-sitter {lang} grammar unavailable")

    def _bind_edges(self, payload):
        return [
            e for e in payload.get("edges", [])
            if e.get("confidence") == "LITERAL_DERIVED"
            and e.get("relation") in ("reads", "writes")
        ]

    def test_captures_survive_cached_fragment_merge(self):
        self._require("java", "sql")
        self.driver.write("db/schema.sql", self._SCHEMA)
        self.driver.write("src/Dao.java", self._DAO)
        self.driver.write("unrelated.py", "def alpha():\n    return 1\n")
        payload = self.driver.build_incremental(set(self.driver.files))
        self.assertTrue(
            _find_edges(payload, source_prefix="src/Dao.java",
                        target="db/schema.sql::users", relation="reads"),
            "full build must mint the embedded-SQL bind edge",
        )
        self.assertEqual(
            (payload.get("merge_stats") or {}).get("sql_capture", {}).get("dynamic_refused"), 1)

        # Edit ONLY the unrelated file: Dao.java's fragment is served from
        # cache — its captures must survive the merge passthrough.
        self.driver.write("unrelated.py", "def alpha():\n    return 2\n")
        payload = self.driver.build_incremental({"unrelated.py"})
        bound = _find_edges(payload, source_prefix="src/Dao.java",
                            target="db/schema.sql::users", relation="reads")
        self.assertTrue(
            bound,
            "bind edge vanished under incremental merge — sql_capture_candidates "
            "dropped from the cached fragment (passthrough regression)",
        )
        self.assertEqual(bound[0].get("confidence"), "LITERAL_DERIVED")
        # The dynamic-refusal count must survive the cached fragment too.
        self.assertEqual(
            (payload.get("merge_stats") or {}).get("sql_capture", {}).get("dynamic_refused"), 1)
        self.assert_equivalent(payload, self.driver.build_oracle(), "after unrelated edit")

    def test_schema_twin_flip_drops_and_restores_bind_in_untouched_file(self):
        # Symbol-delta faithfulness for the RECOMPUTED-each-build bind pass:
        # adding a same-name table in another schema file makes the reference
        # ambiguous (edge drops); deleting it restores the unique bind — with
        # Dao.java untouched throughout.
        self._require("java", "sql")
        self.driver.write("db/schema.sql", self._SCHEMA)
        self.driver.write("src/Dao.java", self._DAO)
        payload = self.driver.build_incremental(set(self.driver.files))
        self.assertTrue(_find_edges(payload, source_prefix="src/Dao.java",
                                    target="db/schema.sql::users", relation="reads"))

        self.driver.write("db/schema2.sql", "CREATE TABLE users (id INT);\n")
        payload = self.driver.build_incremental({"db/schema2.sql"})
        self.assertFalse(
            self._bind_edges(payload),
            "ambiguous table name must DROP the bind edge in the untouched file",
        )
        self.assert_equivalent(payload, self.driver.build_oracle(), "after twin add")

        self.driver.delete("db/schema2.sql")
        payload = self.driver.build_incremental(set(), removed={"db/schema2.sql"})
        self.assertTrue(
            _find_edges(payload, source_prefix="src/Dao.java",
                        target="db/schema.sql::users", relation="reads"),
            "unique table must REBIND after the twin is deleted",
        )
        self.assert_equivalent(payload, self.driver.build_oracle(), "after twin delete")


class OrmEntityMappingIncrementalTests(_IncrementalMergeBase):
    """Wave 1p9qi (1p9qg): `orm_entity_candidates` / `orm_entity_convention` /
    `orm_entity_dynamic` must ride the per-file fragment passthrough — a
    cached (untouched) entity file's declared mapping survives an incremental
    merge, so the finalize bind pass keeps re-minting its `maps_to` edge; and
    the recomputed-each-build pass reacts to schema twins appearing/vanishing
    in OTHER files (unique-match-or-drop stays faithful under deltas)."""

    _SCHEMA = "CREATE TABLE users (id INT PRIMARY KEY);\n"
    _ENTITY = (
        "@Entity\n"
        "@Table(name = \"users\")\n"
        "public class User { }\n"
    )
    _MIXED = (
        "public class Models {}\n"
        "@Entity\n"
        "class ConventionOnly { }\n"
        "@Entity\n"
        "@Table(name = Models.T)\n"
        "class DynamicOne { }\n"
    )

    def _require(self, *langs: str):
        for lang in langs:
            if getattr(self.mod, "_ts_get_parser", lambda *_: None)(lang) is None:
                self.skipTest(f"tree-sitter {lang} grammar unavailable")

    def _maps_to(self, payload):
        return [e for e in payload.get("edges", []) if e.get("relation") == "maps_to"]

    def test_mapping_and_counters_survive_cached_fragment_merge(self):
        self._require("java", "sql")
        self.driver.write("db/schema.sql", self._SCHEMA)
        self.driver.write("src/User.java", self._ENTITY)
        self.driver.write("src/Models.java", self._MIXED)
        self.driver.write("unrelated.py", "def alpha():\n    return 1\n")
        payload = self.driver.build_incremental(set(self.driver.files))
        self.assertTrue(
            _find_edges(payload, source_prefix="src/User.java",
                        target="db/schema.sql::users", relation="maps_to"),
            "full build must mint the entity mapping edge",
        )
        stats = (payload.get("merge_stats") or {}).get("entity_mapping", {})
        self.assertEqual(stats.get("convention_refused"), 1, stats)
        self.assertEqual(stats.get("dynamic_refused"), 1, stats)

        # Edit ONLY the unrelated file: the entity fragments are served from
        # cache — mapping candidates AND refusal counters must survive.
        self.driver.write("unrelated.py", "def alpha():\n    return 2\n")
        payload = self.driver.build_incremental({"unrelated.py"})
        bound = _find_edges(payload, source_prefix="src/User.java",
                            target="db/schema.sql::users", relation="maps_to")
        self.assertTrue(
            bound,
            "mapping edge vanished under incremental merge — orm_entity_candidates "
            "dropped from the cached fragment (passthrough regression)",
        )
        self.assertEqual(bound[0].get("confidence"), "LITERAL_DERIVED")
        stats = (payload.get("merge_stats") or {}).get("entity_mapping", {})
        self.assertEqual(stats.get("convention_refused"), 1, stats)
        self.assertEqual(stats.get("dynamic_refused"), 1, stats)
        self.assert_equivalent(payload, self.driver.build_oracle(), "after unrelated edit")

    def test_schema_twin_flip_drops_and_restores_mapping_in_untouched_file(self):
        self._require("java", "sql")
        self.driver.write("db/schema.sql", self._SCHEMA)
        self.driver.write("src/User.java", self._ENTITY)
        payload = self.driver.build_incremental(set(self.driver.files))
        self.assertTrue(_find_edges(payload, source_prefix="src/User.java",
                                    target="db/schema.sql::users", relation="maps_to"))

        self.driver.write("db/schema2.sql", "CREATE TABLE users (id INT);\n")
        payload = self.driver.build_incremental({"db/schema2.sql"})
        self.assertFalse(
            self._maps_to(payload),
            "ambiguous table name must DROP the mapping edge in the untouched file",
        )
        self.assert_equivalent(payload, self.driver.build_oracle(), "after twin add")

        self.driver.delete("db/schema2.sql")
        payload = self.driver.build_incremental(set(), removed={"db/schema2.sql"})
        self.assertTrue(
            _find_edges(payload, source_prefix="src/User.java",
                        target="db/schema.sql::users", relation="maps_to"),
            "unique table must REBIND the mapping after the twin is deleted",
        )
        self.assert_equivalent(payload, self.driver.build_oracle(), "after twin delete")


if __name__ == "__main__":
    unittest.main()
