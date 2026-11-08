#!/usr/bin/env python3
"""The lifecycle and upgrade import path loads from a zipped framework (wave 22r99, change 22r98).

``review_policy`` hashes ``gardener_metadata``'s source at import. Under zipimport
that module's ``__file__`` lies inside the archive, so the bytes are read through the
module loader rather than the filesystem.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
from framework_files import framework_source_files, source_path  # noqa: E402

# argv[1] is the import root (a zip or the scripts directory). Paths travel through
# argv, never through the program text.
_PROBE = """\
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import review_policy, lifecycle_gate_support, gardener_metadata
old_form = "ok"
try:
    Path(gardener_metadata.__file__).read_bytes()
except NotADirectoryError:
    old_form = "NotADirectoryError"
print(json.dumps({
    "review_policy": review_policy.__file__,
    "lifecycle_gate_support": lifecycle_gate_support.__file__,
    "signature": review_policy.normalizer_signature(),
    "old_form": old_form,
}))
"""


def _probe(import_root: Path) -> dict:
    env = dict(os.environ)
    env.pop("PYTHONPYCACHEPREFIX", None)
    done = subprocess.run(
        [sys.executable, "-B", "-c", _PROBE, str(import_root)],
        capture_output=True, text=True, env=env, timeout=60, cwd=str(import_root.parent),
    )
    if done.returncode != 0:
        raise AssertionError(f"probe failed ({done.returncode}):\n{done.stderr}")
    return json.loads(done.stdout.strip().splitlines()[-1])


class ZippedFrameworkImportTests(unittest.TestCase):
    def test_review_policy_and_lifecycle_gate_support_import_from_a_sources_zip(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "framework-scripts.zip"
            with zipfile.ZipFile(archive, "w") as zipped:
                # The shippable tree: flat modules, their aliases and the package.
                for source in framework_source_files(include_aliases=True):
                    zipped.write(source, source.relative_to(SCRIPTS).as_posix())
            from_zip = _probe(archive)
            from_tree = _probe(SCRIPTS)
        prefix = str(archive) + os.sep
        self.assertTrue(from_zip["review_policy"].startswith(prefix), from_zip)
        self.assertTrue(from_zip["lifecycle_gate_support"].startswith(prefix), from_zip)
        self.assertEqual(from_zip["signature"], from_tree["signature"])
        # The signature is the hash of the normalizer module's own source bytes.
        self.assertEqual(from_tree["signature"],
                         hashlib.sha256((SCRIPTS / "gardener_metadata.py").read_bytes()).hexdigest())
        # Known-bad control: the previous filesystem read cannot work from the zip.
        self.assertEqual(from_zip["old_form"], "NotADirectoryError")
        self.assertEqual(from_tree["old_form"], "ok")


# Wave 22u26 (22u24): index_compatibility captures nine producer sources at import. argv[1] is the
# sys.path entry, exactly as given (it may be relative to the probe's working directory).
_INDEX_PROBE = """\
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import index_compatibility, operational_evidence
index_compatibility.ensure_runtime_current()
old_form = "ok"
try:
    (Path(index_compatibility.__file__).resolve().parent / "indexer.py").read_bytes()
except OSError as exc:
    old_form = type(exc).__name__
print(json.dumps({
    "index_compatibility": index_compatibility.__file__,
    "operational_evidence": operational_evidence.__file__,
    "hashes": index_compatibility._SOURCE_HASHES,
    "supported": index_compatibility.SUPPORTED,
    "old_form": old_form,
}))
"""


def _index_probe(import_entry: str, cwd: Path) -> dict:
    env = dict(os.environ)
    env.pop("PYTHONPYCACHEPREFIX", None)
    done = subprocess.run(
        [sys.executable, "-B", "-c", _INDEX_PROBE, import_entry],
        capture_output=True, text=True, env=env, timeout=60, cwd=str(cwd),
    )
    if done.returncode != 0:
        raise AssertionError(f"index probe failed ({done.returncode}):\n{done.stderr}")
    return json.loads(done.stdout.strip().splitlines()[-1])


def _write_sources_zip(archive: Path) -> None:
    with zipfile.ZipFile(archive, "w") as zipped:
        for source in framework_source_files(include_aliases=True):
            zipped.write(source, source.relative_to(SCRIPTS).as_posix())


class ZippedIndexCompatibilityImportTests(unittest.TestCase):
    def test_index_compatibility_captures_the_same_sources_from_a_zip(self):
        from_tree = _index_probe(str(SCRIPTS), SCRIPTS.parent)
        self.assertEqual(from_tree["old_form"], "ok")
        with tempfile.TemporaryDirectory() as tmp:
            real = Path(tmp) / "real"
            real.mkdir()
            archive = real / "framework-scripts.zip"
            _write_sources_zip(archive)
            cases = [("absolute", str(archive), Path(tmp)), ("relative", "./framework-scripts.zip", real)]
            link = Path(tmp) / "link"
            try:
                link.symlink_to(real, target_is_directory=True)
            except (OSError, NotImplementedError):
                link = None  # Windows without symlink privilege: the other two cases still run
            if link is not None:
                cases.append(("symlinked", str(link / "framework-scripts.zip"), Path(tmp)))
            for label, entry, cwd in cases:
                with self.subTest(case=label):
                    from_zip = _index_probe(entry, cwd)
                    # Both modules came from inside the archive, as the entry spells it.
                    for module in ("index_compatibility", "operational_evidence"):
                        self.assertTrue(from_zip[module].startswith(entry + os.sep)
                                        or from_zip[module].startswith(entry + "/"), from_zip)
                    self.assertEqual(from_zip["hashes"], from_tree["hashes"])
                    self.assertEqual(from_zip["supported"], from_tree["supported"])
                    # Known-bad control: the previous filesystem read cannot work from the zip.
                    self.assertEqual(from_zip["old_form"], "NotADirectoryError")
        self.assertEqual(sorted(from_tree["hashes"]), sorted(
            ("indexer", "chunker", "graph_indexer", "graph_store", "sqlite_vector_store",
             "index_state_store", "model_bundle", "marker_namespaces", "operational_evidence")))


class FilesystemSourceCaptureTests(unittest.TestCase):
    """Non-regression guard: the filesystem capture and staleness check are unchanged."""

    def setUp(self):
        if str(SCRIPTS) not in sys.path:
            sys.path.insert(0, str(SCRIPTS))
        import index_compatibility
        self.ic = index_compatibility

    def test_each_captured_hash_is_the_producer_file_hash(self):
        for name, digest in self.ic._SOURCE_HASHES.items():
            with self.subTest(producer=name):
                self.assertEqual(digest, hashlib.sha256(source_path(name).read_bytes()).hexdigest())

    def test_a_changed_or_missing_producer_is_reported_stale(self):
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            copies = Path(tmp)
            for name in self.ic._SOURCE_NAMES:
                (copies / f"{name}.py").write_bytes(source_path(name).read_bytes())
            with mock.patch.object(self.ic, "_SOURCE_ROOT", copies):
                self.ic.ensure_runtime_current()
                (copies / "chunker.py").write_bytes(source_path("chunker").read_bytes() + b"\n# changed\n")
                with self.assertRaises(self.ic.IndexCompatibilityError) as changed:
                    self.ic.ensure_runtime_current()
                self.assertEqual((changed.exception.code, changed.exception.component), ("index_runtime_stale", "chunker"))
                (copies / "chunker.py").unlink()
                with self.assertRaises(self.ic.IndexCompatibilityError) as missing:
                    self.ic.ensure_runtime_current()
                self.assertEqual((missing.exception.code, missing.exception.persisted), ("index_runtime_stale", None))


if __name__ == "__main__":
    unittest.main()
