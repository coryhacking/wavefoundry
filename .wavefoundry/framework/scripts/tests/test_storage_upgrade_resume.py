"""Native regression coverage for pack resume and explicit storage rebuild.

Pack-resume probes stop at surface rendering and invoke real schema conversion.
Rebuild probes use ordinary parent-owned indexing with real chunkers, SQLite,
graph, fresh verification and cleanup. Their fresh children substitute only
model inference and bypass setup dependency provisioning; no source, receipt,
pack, host, conversion or publication guard is mocked in positive paths.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import zipfile

SCRIPTS = Path(__file__).resolve().parents[1]
REPO = SCRIPTS.parents[2]
sys.path.insert(0, str(SCRIPTS))
import upgrade_protocol
import index_paths
import sqlite_storage_migration as migration
import upgrade_lib

# A separate driver process imports exactly the on-disk runner named by the
# emitted command, then gives main its emitted arguments unchanged.
DRIVER = r'''
import importlib.util, json, pathlib, sys
runner, arguments = pathlib.Path(sys.argv[1]), json.loads(sys.argv[2])
sys.path.insert(0, str(runner.parent))
spec = importlib.util.spec_from_file_location("upgrade_wavefoundry", runner)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)
# The storage hooks and dispatcher remain real. Stop before unrelated rendering.
def conversion_boundary(root):
    import sqlite_storage_migration
    result = sqlite_storage_migration.migrate_legacy(root)
    (root / "conversion-boundary.json").write_text(json.dumps(result))
    raise SystemExit(77)
mod.phase_surface_rendering = conversion_boundary
raise SystemExit(mod.main(arguments))
'''


def _native_available():
    try:
        import sqlite_runtime
        with tempfile.TemporaryDirectory() as directory:
            sqlite_runtime.connect(Path(directory) / "probe.sqlite").close()
        return True
    except (ImportError, RuntimeError):
        return False


@unittest.skipUnless(_native_available(), "qualified APSW + sqlite-vec runtime unavailable")
class StorageUpgradeProcessResumeTests(unittest.TestCase):
    TARGET = "1.23.0+resume"
    OLD_MANIFEST = b"MANIFEST\r\nVERSION\r\nseeds/retired.md\r\n"

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="wf resume ")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / "target with spaces"
        self.framework = self.root / ".wavefoundry/framework"
        self.installed = self.framework / "scripts"
        shutil.copytree(SCRIPTS, self.installed, ignore=shutil.ignore_patterns("tests", "__pycache__"))
        self.runner = self.installed / "upgrade_wavefoundry.py"
        if self._testMethodName.startswith("test_old_main"):
            old = subprocess.run(
                ["git", "show", "v1.22.0:.wavefoundry/framework/scripts/upgrade_wavefoundry.py"],
                cwd=REPO, capture_output=True)
            if old.returncode:
                self.skipTest("v1.22.0 tag unavailable (historical-runner integration requires full history)")
            self.runner.write_bytes(old.stdout)
        (self.framework / "VERSION").write_text("1.22.0\n")
        (self.framework / "MANIFEST").write_bytes(self.OLD_MANIFEST)
        (self.framework / "seeds").mkdir()
        (self.framework / "seeds/retired.md").write_text("old managed seed\n")
        (self.root / "docs").mkdir()
        (self.root / "docs/workflow-config.json").write_text("{}\n")
        self.bootstrap = self.root / "install-wavefoundry.md"
        self.bootstrap.write_bytes(b"tracked project installer\n")
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        subprocess.run(["git", "-C", str(self.root), "add", "install-wavefoundry.md"], check=True)
        self.bootstrap.write_bytes(b"tracked project installer with local modifications\r\n")
        self.original_bootstrap = self.bootstrap.read_bytes()
        self.index = self.root / ".wavefoundry/index"
        self.index.mkdir()
        self.source = index_paths.legacy_index_database_path(self.index)
        self.database = index_paths.index_database_path(self.index)
        with contextlib.closing(sqlite3.connect(self.source)) as db, db:
            db.execute("CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
            db.execute("INSERT INTO meta VALUES('store_schema_version','6')")
            db.execute("CREATE TABLE preserved_memory(id TEXT PRIMARY KEY,body TEXT)")
            db.execute("INSERT INTO preserved_memory VALUES('memory-1','retain me')")
        self.database_before = self.source.read_bytes()
        # The legacy runner discovers its original locator through its ambient
        # finder; a highest-version fixture in the target wins over host packs.
        # The protocol/VERSION inside is the actual 1.23.0 target authority.
        self.pack = self.root / "wavefoundry-99.0.0.resume.zip"
        with zipfile.ZipFile(self.pack, "w", zipfile.ZIP_DEFLATED) as archive:
            for source in sorted(SCRIPTS.rglob("*.py")):
                if "tests" not in source.relative_to(SCRIPTS).parts and "__pycache__" not in source.parts:
                    archive.write(source, ".wavefoundry/framework/scripts/" + source.relative_to(SCRIPTS).as_posix())
            archive.writestr(".wavefoundry/framework/VERSION", self.TARGET + "\n")
            archive.writestr(".wavefoundry/framework/MANIFEST", "MANIFEST\nVERSION\n")
            archive.writestr("install-wavefoundry.md", "incoming single-use installer\n")
            archive.writestr(upgrade_protocol.PROTOCOL_METADATA_ARCNAME, json.dumps(
                upgrade_protocol.build_protocol_metadata(release_version="1.23.0", build_id="resume", artifact_type="feature")))
        self.driver = self.base / "driver.py"
        self.driver.write_text(DRIVER)

    def attempt(self, argv):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", WAVEFOUNDRY_SKIP_PYTHON_HEAL="1")
        env.pop(migration.CONFIRM_ENV, None)
        result = subprocess.run([argv[0], "-B", str(self.driver), argv[1], json.dumps(argv[2:])],
                              cwd=self.root, env=env, capture_output=True, text=True, timeout=90)
        lock = upgrade_lib.read_upgrade_lock(self.root) or {}
        consumed = Path(lock.get("zip_path") or ".")
        if consumed.name.startswith("wf-verified-pack-") and consumed.is_file():
            self.addCleanup(consumed.unlink, missing_ok=True)
        return result

    def pause(self):
        first = self.attempt([sys.executable, str(self.runner), "--root", str(self.root),
                              "--pack", str(self.pack), "--yes"])
        self.assertEqual(first.returncode, 3, first.stdout + first.stderr)
        receipt = migration.read_receipt(self.index)
        self.assertIsNotNone(receipt, first.stdout + first.stderr)
        self.assertEqual(receipt["state"], "restart_required")
        self.assertEqual(self.source.read_bytes(), self.database_before)
        self.assertEqual(self.bootstrap.read_bytes(), self.original_bootstrap)
        self.assertFalse((self.root / "conversion-boundary.json").exists())
        self.assertEqual(self.runner.read_bytes(), (SCRIPTS / "upgrade_wavefoundry.py").read_bytes())
        self.assertEqual(receipt["pack_sha256"], hashlib.sha256(self.pack.read_bytes()).hexdigest())
        self.assertEqual(Path(receipt["pack_path"]), self.pack)
        staged = Path(receipt["restart_action"]["consumed_pack_path"])
        self.assertNotEqual(staged, self.pack)
        self.assertTrue(staged.name.startswith("wf-verified-pack-"))
        staged.unlink(missing_ok=True)
        return receipt

    def test_current_main_generated_command_restarts_with_new_private_copy(self):
        receipt = self.pause()
        resumed = self.attempt(receipt["restart_action"]["command_argv"])
        self.assertEqual(resumed.returncode, 77, resumed.stdout + resumed.stderr)
        converted = json.loads((self.root / "conversion-boundary.json").read_text())
        self.assertEqual(converted["state"], "published")
        self.assertEqual(converted["migration_id"], receipt["migration_id"])
        self.assertEqual(self.bootstrap.read_bytes(), self.original_bootstrap)

    def test_old_main_pause_then_fresh_installed_main_relocated_pack_and_retry(self):
        receipt = self.pause()
        # Locate the actual durable snapshot without depending on its filename.
        snapshots = [p for p in (self.root / ".wavefoundry").glob("*manifest*") if p.is_file()]
        self.assertTrue(snapshots)
        saved_snapshots = {p: p.read_bytes() for p in snapshots}
        self.assertTrue(any(json.loads(body).get("manifest", "").encode() == self.OLD_MANIFEST
                            for body in saved_snapshots.values()))
        relocated = self.base / "relocated original pack.zip"
        self.pack.rename(relocated)
        bad = self.base / "changed same VERSION pack.zip"
        with zipfile.ZipFile(relocated) as source, zipfile.ZipFile(bad, "w") as changed:
            for entry in source.infolist():
                changed.writestr(entry, source.read(entry.filename))
            changed.writestr("different-content.txt", "different bytes, identical VERSION\n")
        upgrade_protocol.validate_feature_pack(bad)
        argv = receipt["restart_action"]["command_argv"]
        self.assertEqual(argv[1], str(self.runner))
        self.assertIn("--confirm-hosts-stopped", argv)
        argv[argv.index("--pack") + 1] = str(bad)
        failed = self.attempt(argv)
        self.assertNotEqual(failed.returncode, 77, failed.stdout + failed.stderr)
        self.assertIn("storage_pack_changed", failed.stdout + failed.stderr)
        self.assertEqual(self.source.read_bytes(), self.database_before)
        self.assertEqual(self.bootstrap.read_bytes(), self.original_bootstrap)
        self.assertEqual(migration.read_receipt(self.index)["migration_id"], receipt["migration_id"])
        for path, body in saved_snapshots.items():
            self.assertEqual(path.read_bytes(), body)
        argv[argv.index("--pack") + 1] = str(relocated)
        resumed = self.attempt(argv)
        self.assertEqual(resumed.returncode, 77, resumed.stdout + resumed.stderr)
        converted = json.loads((self.root / "conversion-boundary.json").read_text())
        self.assertEqual(converted["state"], "published")
        self.assertEqual(converted["migration_id"], receipt["migration_id"])
        self.assertEqual(self.bootstrap.read_bytes(), self.original_bootstrap)
        with contextlib.closing(sqlite3.connect(self.database)) as db, db:
            self.assertEqual(db.execute("SELECT body FROM preserved_memory").fetchone(), ("retain me",))
            self.assertEqual(db.execute("SELECT value FROM meta WHERE key='store_schema_version'").fetchone(),
                             (migration.SCHEMA_VERSION,))
        for path, body in saved_snapshots.items():
            self.assertEqual(path.read_bytes(), body)
        self.assertTrue((self.framework / "seeds/retired.md").exists())
        rollback = self.index / converted["work_dir"] / migration.STAGING_ROLLBACK_STEM
        self.assertTrue(rollback.is_file())
        with contextlib.closing(sqlite3.connect(rollback)) as db:
            self.assertEqual(db.execute("SELECT body FROM preserved_memory").fetchone(), ("retain me",))
            self.assertEqual(db.execute("SELECT value FROM meta WHERE key='store_schema_version'").fetchone(), ("6",))



# This child preserves the runner-selected full/content modes and exercises the
# real walker, current chunkers, writer, graph builder and publication staging.
# Only model inference is deterministic; setup's dependency/network layer is
# outside this regression and is separately exercised by packaging tests.
REBUILD_CHILD = r'''
import json, os, pathlib, sys
sys.path.insert(0, sys.argv[1])
import numpy as np
import indexer
class Embedder:
    def embed(self, texts, batch_size=256):
        for text in texts:
            if os.environ.get("WF_TEST_EMBED_FAILURE") == "1":
                raise RuntimeError("injected model inference failure")
            value = np.zeros(384, dtype=np.float32)
            value[0], value[1] = 1, (len(text) % 13) / 13
            yield value
indexer._get_embedder = lambda *a, **kw: Embedder()
args = json.loads(sys.argv[2])
root = pathlib.Path(args[args.index("--root") + 1])
if os.environ.get("WF_TEST_READ_FAILURE") == "1":
    original_read = pathlib.Path.read_text
    def fail_source(path, *a, **kw):
        if path == root / "docs/current.md":
            raise PermissionError("injected current source read failure")
        return original_read(path, *a, **kw)
    pathlib.Path.read_text = fail_source
content = "graph" if "--graph-only" in args else os.environ.get("WF_TEST_CONTENT", "all")
result = indexer.build_index(root, full="--full" in args, content=content)
print("REBUILD_TEST_RESULT:" + json.dumps(result, default=str))
raise SystemExit(0 if result.get("status") != "failed" and not result.get("failure") else 2)
'''


def _legacy_available():
    try:
        import lancedb
        return True
    except ImportError:
        return False


@unittest.skipUnless(_native_available() and _legacy_available(), "qualified SQLite and legacy Lance reader unavailable")
class StorageRebuildPublicationTests(unittest.TestCase):
    """Real duplicate source, actual parent orchestration, native child builds."""

    def setUp(self):
        from types import SimpleNamespace
        self.tmp = tempfile.TemporaryDirectory(prefix="wf rebuild ")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.index = self.root / ".wavefoundry/index"
        self.index.mkdir(parents=True)
        (self.root / "docs").mkdir()
        (self.root / "src").mkdir()
        (self.root / "docs/workflow-config.json").write_text("{}\n")
        (self.root / "docs/current.md").write_text(
            "# Current document\n\nFresh alpha source.\n\n## Repeated\n\nOne current section.\n\n## Repeated\n\nAnother current section.\n")
        (self.root / "src/current.py").write_text(
            'class First:\n    def repeat(self):\n        """Current source alpha."""\n        return 1\n\n'
            'class Second:\n    def repeat(self):\n        """Current source beta."""\n        return 2\n')
        (self.root / "src/Overloads.java").write_text(
            'public class Overloads {\n'
            ' public String find(String value) { return "stringoverloadmarker"; }\n'
            ' public String find(int value) { return "integeroverloadmarker"; }\n'
            '}\n')
        import lancedb
        old = {"id": "duplicate-legacy-id", "path": "docs/current.md", "kind": "docs",
               "text": "obsolete collision payload", "start_line": 1, "end_line": 1,
               "vector": [1.0] + [0.0] * 383}
        legacy = lancedb.connect(str(self.index))
        legacy.create_table("docs", [old])
        java = {**old, "id": "src/Overloads.java::Overloads.find", "path": "src/Overloads.java", "kind": "code"}
        legacy.create_table("code", [
            {**java, "text": 'public String find(String value) { return "obsolete collision string"; }'},
            {**java, "text": 'public String find(int value) { return "obsolete collision integer"; }'},
        ])
        self.source = index_paths.legacy_index_database_path(self.index)
        self.live = index_paths.index_database_path(self.index)
        with contextlib.closing(sqlite3.connect(self.source)) as db, db:
            db.execute("CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
            db.execute("INSERT INTO meta VALUES('store_schema_version','6')")
            db.execute("CREATE TABLE preserved_memory(id TEXT PRIMARY KEY,body TEXT)")
            db.execute("INSERT INTO preserved_memory VALUES('memory-1','retain me')")
        self.original = self.source.read_bytes()
        self.ctx = SimpleNamespace(root=self.root, from_version="1.22.0", to_version="1.23.0+rebuild",
                                   zip_path=None, dry_run=False, storage_migration_protocol=1)
        from unittest.mock import patch
        import io
        with patch.dict(os.environ, {migration.CONFIRM_ENV: "0"}), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit):
                migration.prepare_upgrade(self.ctx)
        with patch.dict(os.environ, {migration.CONFIRM_ENV: "1"}):
            migration.prepare_upgrade(self.ctx)
        # Keep the test harness out of the repository walk and graph inventory.
        self.child = self.index / "rebuild-child.py"
        self.child.write_text(REBUILD_CHILD)

    def select_rebuild(self):
        from unittest.mock import patch
        self.ctx.rebuild_storage = True
        with patch.dict(os.environ, {migration.CONFIRM_ENV: "1"}):
            migration.prepare_upgrade(self.ctx)
        self.assertEqual(migration.read_receipt(self.index)["strategy"], "rebuild")

    def run_parent(self, failure=None):
        import io
        import memory_backfill
        import upgrade_wavefoundry as upgrade
        from unittest.mock import patch
        run_id = memory_backfill.ensure_run(self.root, "upgrade")
        memory_backfill.sync_inventory(self.root, run_id)
        observed = []
        def run(argv, **kwargs):
            if Path(argv[1]).name == "setup_index.py":
                if "--prewarm-only" in argv:
                    # The deterministic embedder below requires no download or
                    # native model session; retain the real prewarm ordering.
                    self.assertTrue((self.index / "docs.lance").exists())
                    return subprocess.CompletedProcess(argv, 2 if failure == "prewarm" else 0)
                observed.append(("graph" if "--graph-only" in argv else "all", "--full" in argv))
                child_env = dict(os.environ)
                child_env.update(kwargs.get("env", {}))
                child_env["PYTHONDONTWRITEBYTECODE"] = "1"
                if failure == "graph" and "--graph-only" in argv:
                    return subprocess.CompletedProcess(argv, 2)
                if failure == "false_success" and "--graph-only" not in argv:
                    return subprocess.CompletedProcess(argv, 0)
                if failure == "partial" and "--graph-only" not in argv:
                    child_env["WF_TEST_CONTENT"] = "docs"
                if failure == "read" and "--graph-only" not in argv:
                    child_env["WF_TEST_READ_FAILURE"] = "1"
                if failure == "embedding" and "--graph-only" not in argv:
                    child_env["WF_TEST_EMBED_FAILURE"] = "1"
                completed = subprocess.run([sys.executable, "-B", str(self.child), str(SCRIPTS), json.dumps(argv[2:])],
                                           env=child_env, cwd=self.root, capture_output=True, text=True, timeout=90)
                self.child_output = completed.stdout + completed.stderr
                if failure == "delete_layer" and "--graph-only" not in argv and completed.returncode == 0:
                    import sqlite_runtime
                    with contextlib.closing(sqlite_runtime.connect(self.live)) as conn:
                        conn.execute("DELETE FROM chunks_code")
                return completed
            return subprocess.run(argv, capture_output=True, text=True, check=False,
                                  **{key: value for key, value in kwargs.items() if key not in {"check", "capture_output", "text"}})
        # Dependency installation and model warming are the model seam. The
        # qualified runtime and deterministic child embedder are already present.
        import setup_index
        import index_state_store
        with contextlib.ExitStack() as controls, memory_backfill.index_publication_scope(run_id), \
             patch.object(upgrade.subprocess_util, "isolated_run", side_effect=run), \
             patch.object(setup_index, "ensure_deps"), \
             patch.object(setup_index, "prewarm_models"), \
             contextlib.redirect_stdout(io.StringIO()):
            if failure == "before_finalize":
                controls.enter_context(patch.object(index_state_store, "finalize_staged_build_epoch",
                    side_effect=RuntimeError("injected interruption before parent publication")))
            upgrade.phase_index_update_parent_owned(self.root, run_id)
        return observed

    def test_duplicate_transfer_refuses_then_explicit_rebuild_publishes_current_sources(self):
        with self.assertRaisesRegex(Exception, "UNIQUE|duplicate"):
            migration.migrate_legacy(self.root)
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertTrue((self.index / "docs.lance").is_dir())
        self.assertEqual(migration.read_receipt(self.index)["state"], "quiesced")
        self.select_rebuild()
        observed = self.run_parent()
        self.assertEqual(observed, [("all", True), ("graph", True)], getattr(self, "child_output", ""))
        self.assertEqual(migration.read_receipt(self.index)["state"], "verified")
        import sqlite_vector_store as vectors
        for layer in ("docs", "code"):
            rows = vectors.payload_rows(self.index, layer)
            self.assertTrue(rows, layer)
            self.assertEqual(len({row["id"] for row in rows}), len(rows))
            self.assertFalse(any("obsolete collision" in row["text"] for row in rows))
        java_rows = [row for row in vectors.payload_rows(self.index, "code")
                     if row["path"] == "src/Overloads.java"]
        self.assertTrue(java_rows)
        self.assertEqual(len({row["id"] for row in java_rows}), len(java_rows))
        self.assertTrue(any('find(String value)' in row["text"] for row in java_rows))
        self.assertTrue(any('find(int value)' in row["text"] for row in java_rows))
        with contextlib.closing(sqlite3.connect(self.live)) as db:
            self.assertEqual(db.execute("SELECT body FROM preserved_memory").fetchone(), ("retain me",))
            for marker in ("stringoverloadmarker", "integeroverloadmarker"):
                self.assertGreater(db.execute("SELECT count(*) FROM fts_code WHERE fts_code MATCH ?", (marker,)).fetchone()[0], 0)
        self.assertEqual(migration.cleanup_legacy(self.root)["state"], "complete")
        self.assertFalse((self.index / "docs.lance").exists())
        self.assertFalse((self.index / "code.lance").exists())

    def test_interrupted_embedding_retains_originals_and_retries_full_both_layers(self):
        self.select_rebuild()
        with self.assertRaises(RuntimeError):
            self.run_parent("embedding")
        self.assertTrue((self.index / "docs.lance").is_dir())
        receipt = migration.read_receipt(self.index)
        self.assertEqual(receipt["strategy"], "rebuild")
        self.assertTrue((self.index / receipt["work_dir"] / "rollback.sqlite").exists())
        with self.assertRaises(migration.MigrationRequired):
            migration.cleanup_legacy(self.root)
        observed = self.run_parent()
        self.assertEqual(observed, [("all", True), ("graph", True)], getattr(self, "child_output", ""))
        self.assertEqual(migration.read_receipt(self.index)["state"], "verified")
        self.assertEqual(migration.cleanup_legacy(self.root)["state"], "complete")

    def test_success_exit_without_semantic_build_cannot_verify_empty_candidate(self):
        self.select_rebuild()
        with self.assertRaises(RuntimeError):
            self.run_parent("false_success")
        self.assertTrue((self.index / "docs.lance").is_dir())
        with self.assertRaises(migration.MigrationRequired):
            migration.cleanup_legacy(self.root)
        self.assertNotEqual(migration.read_receipt(self.index)["state"], "verified")

    def test_missing_semantic_layer_cannot_authorize_cleanup(self):
        self.select_rebuild()
        with self.assertRaises(RuntimeError):
            self.run_parent("delete_layer")
        self.assertTrue((self.index / "docs.lance").is_dir())
        with self.assertRaises(migration.MigrationRequired):
            migration.cleanup_legacy(self.root)

    def test_requested_partial_scope_is_forced_to_both_semantic_layers(self):
        self.select_rebuild()
        self.run_parent("partial")
        import sqlite_vector_store as vectors
        counts = vectors.layer_counts(self.index)
        self.assertGreater(counts["docs"], 0)
        self.assertGreater(counts["code"], 0)
        self.assertEqual(migration.read_receipt(self.index)["state"], "verified")

    def test_semantic_proof_from_failed_graph_attempt_cannot_authorize_skipped_retry(self):
        self.select_rebuild()
        with self.assertRaisesRegex(RuntimeError, "Graph index update failed"):
            self.run_parent("graph")
        import sqlite_runtime
        with contextlib.closing(sqlite_runtime.connect(self.live)) as conn:
            self.assertIsNotNone(conn.execute("SELECT value FROM meta WHERE key='storage_rebuild_proof'").fetchone())
        with self.assertRaises(migration.MigrationRequired):
            migration.cleanup_legacy(self.root)
        with self.assertRaises(RuntimeError):
            self.run_parent("false_success")
        self.assertTrue((self.index / "docs.lance").exists())
        self.assertTrue((self.index / "code.lance").exists())
        with self.assertRaises(migration.MigrationRequired):
            migration.cleanup_legacy(self.root)
        self.run_parent()
        self.assertEqual(migration.read_receipt(self.index)["state"], "verified")
        self.assertEqual(migration.cleanup_legacy(self.root)["state"], "complete")

    def test_model_prewarm_failure_precedes_cutover(self):
        self.select_rebuild()
        with self.assertRaisesRegex(migration.MigrationRequired, "models_unavailable"):
            self.run_parent("prewarm")
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertTrue((self.index / "docs.lance").exists())
        self.assertNotIn("work_dir", migration.read_receipt(self.index))

    def test_stale_semantic_proof_cannot_reuse_parent_staging_and_retry_rebuilds(self):
        self.select_rebuild()
        with self.assertRaisesRegex(RuntimeError, "injected interruption"):
            self.run_parent("before_finalize")
        staging = self.index / "upgrade-index-staging-receipt.json"
        self.assertTrue(staging.exists())
        import sqlite_runtime
        with contextlib.closing(sqlite_runtime.connect(self.live)) as conn:
            value = conn.execute("SELECT value FROM meta WHERE key='storage_rebuild_proof'").fetchone()
            self.assertIsNotNone(value)
            proof = json.loads(value[0])
            proof["rebuild_id"] = "0" * 32
            conn.execute("UPDATE meta SET value=? WHERE key='storage_rebuild_proof'", (json.dumps(proof),))
        with self.assertRaises(migration.MigrationRequired):
            migration.cleanup_legacy(self.root)
        try:
            observed = self.run_parent()
        except RuntimeError as exc:
            self.fail("stale stage must trigger a real rebuild before verification: " + str(exc))
        self.assertEqual(observed, [("all", True), ("graph", True)], getattr(self, "child_output", ""))
        self.assertFalse(staging.exists())
        self.assertEqual(migration.read_receipt(self.index)["state"], "verified")
        self.assertEqual(migration.cleanup_legacy(self.root)["state"], "complete")

    def test_unreadable_current_source_fails_closed_and_retry_uses_current_chunker(self):
        self.select_rebuild()
        with self.assertRaises(RuntimeError):
            self.run_parent("read")
        self.assertIn("injected current source read failure", self.child_output)
        self.assertTrue((self.index / "docs.lance").is_dir())
        with self.assertRaises(migration.MigrationRequired):
            migration.cleanup_legacy(self.root)
        self.run_parent()
        self.assertEqual(migration.read_receipt(self.index)["state"], "verified")


if __name__ == "__main__":
    unittest.main()
