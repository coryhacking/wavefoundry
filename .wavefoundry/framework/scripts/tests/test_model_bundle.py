import json
import os
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import model_bundle
import upgrade_wavefoundry


class ModelBundleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.cache = self.tmp / "source-cache"
        for _id, target, directory, _license, _upstream in model_bundle.COMPONENTS:
            base = self.cache / target / directory
            (base / "refs").mkdir(parents=True)
            (base / "snapshots" / "rev" / "onnx").mkdir(parents=True)
            (base / "refs" / "main").write_text("rev\n", encoding="utf-8")
            (base / "snapshots" / "rev" / "onnx" / "model.onnx").write_bytes(directory.encode())
        self.out = self.tmp / "out"; self.out.mkdir()
        self.fast = self.tmp / "target-fast"
        self.onnx = self.tmp / "target-onnx"
        self.old_fast, self.old_onnx = os.environ.get("FASTEMBED_CACHE_PATH"), os.environ.get("WAVEFOUNDRY_ONNX_SRC_CACHE")
        os.environ["FASTEMBED_CACHE_PATH"] = str(self.fast)
        os.environ["WAVEFOUNDRY_ONNX_SRC_CACHE"] = str(self.onnx)

    def tearDown(self):
        if self.old_fast is None: os.environ.pop("FASTEMBED_CACHE_PATH", None)
        else: os.environ["FASTEMBED_CACHE_PATH"] = self.old_fast
        if self.old_onnx is None: os.environ.pop("WAVEFOUNDRY_ONNX_SRC_CACHE", None)
        else: os.environ["WAVEFOUNDRY_ONNX_SRC_CACHE"] = self.old_onnx
        shutil.rmtree(self.tmp)

    def test_build_materialize_and_reuse(self):
        bundle = model_bundle.build_bundle(self.out, cache_root=self.cache)
        self.assertEqual(bundle.name, "wavefoundry-models-1.zip")
        result = model_bundle.materialize_bundle(bundle, expected_model_set_version="1")
        self.assertEqual(result["published_components"], len(model_bundle.COMPONENTS))
        self.assertEqual(model_bundle.materialize_bundle(bundle, expected_model_set_version="1")["published_components"], 0)
        self.assertTrue((self.fast / "models--snowflake--snowflake-arctic-embed-xs" / ".wavefoundry-model-bundle.json").is_file())

    def test_rejects_traversal_and_hash_tamper(self):
        bundle = model_bundle.build_bundle(self.out, cache_root=self.cache)
        bad = self.out / "bad.zip"
        with zipfile.ZipFile(bundle) as source, zipfile.ZipFile(bad, "w") as target:
            for info in source.infolist():
                target.writestr(info.filename, source.read(info.filename))
            target.writestr("models/../../escape", b"bad")
        with self.assertRaisesRegex(RuntimeError, "unsafe path|payload differs"):
            model_bundle.materialize_bundle(bad)

        tampered = self.out / "tampered.zip"
        with zipfile.ZipFile(bundle) as source, zipfile.ZipFile(tampered, "w") as target:
            for info in source.infolist():
                data = source.read(info.filename)
                if info.filename.endswith("model.onnx"):
                    data = b"changed"
                target.writestr(info.filename, data)
        with self.assertRaisesRegex(RuntimeError, "hash mismatch"):
            model_bundle.materialize_bundle(tampered)

        linked = self.out / "linked.zip"
        with zipfile.ZipFile(bundle) as source, zipfile.ZipFile(linked, "w") as target:
            for info in source.infolist():
                target.writestr(info.filename, source.read(info.filename))
            link = zipfile.ZipInfo("models/link")
            link.external_attr = 0o120777 << 16
            target.writestr(link, "target")
        with self.assertRaisesRegex(RuntimeError, "unsafe path|link"):
            model_bundle.materialize_bundle(linked)

    def test_rejects_model_set_version_mismatch(self):
        bundle = model_bundle.build_bundle(self.out, cache_root=self.cache)
        with self.assertRaisesRegex(RuntimeError, "does not match"):
            model_bundle.materialize_bundle(bundle, expected_model_set_version="9.9.9")

    def test_repairs_corrupt_cache(self):
        bundle = model_bundle.build_bundle(self.out, cache_root=self.cache)
        model_bundle.materialize_bundle(bundle)
        cached = self.fast / "models--snowflake--snowflake-arctic-embed-xs" / "snapshots" / "rev" / "onnx" / "model.onnx"
        cached.write_bytes(b"corrupt")
        self.assertEqual(model_bundle.materialize_bundle(bundle)["published_components"], 1)

    def test_newer_model_set_replaces_and_older_set_does_not_downgrade(self):
        bundle = model_bundle.build_bundle(self.out, cache_root=self.cache)
        model_bundle.materialize_bundle(bundle)
        newer = self.out / "newer.zip"
        with zipfile.ZipFile(bundle) as source, zipfile.ZipFile(newer, "w") as target:
            for info in source.infolist():
                data = source.read(info.filename)
                if info.filename == "model-bundle-manifest.json":
                    manifest = json.loads(data)
                    manifest["model_set_version"] = "2"
                    data = json.dumps(manifest).encode("utf-8")
                target.writestr(info.filename, data)
        self.assertEqual(model_bundle.materialize_bundle(newer)["published_components"], len(model_bundle.COMPONENTS))
        self.assertEqual(model_bundle.materialize_bundle(bundle)["published_components"], 0)

    def test_standard_package_check_reports_older_managed_set(self):
        bundle = model_bundle.build_bundle(self.out, cache_root=self.cache)
        model_bundle.materialize_bundle(bundle)
        for _component_id, target, directory, _license_id, _upstream in model_bundle.COMPONENTS:
            marker = model_bundle._target_root(target) / directory / ".wavefoundry-model-bundle.json"
            value = json.loads(marker.read_text(encoding="utf-8"))
            value["model_set_version"] = "0"
            marker.write_text(json.dumps(value), encoding="utf-8")
        self.assertEqual(model_bundle.local_model_set_status(), "older")

    def test_failed_publish_restores_existing_cache(self):
        bundle = model_bundle.build_bundle(self.out, cache_root=self.cache)
        model_bundle.materialize_bundle(bundle)
        old_markers: dict[Path, str] = {}
        for _component_id, target, directory, _license_id, _upstream in model_bundle.COMPONENTS:
            marker = model_bundle._target_root(target) / directory / ".wavefoundry-model-bundle.json"
            value = json.loads(marker.read_text(encoding="utf-8"))
            value["model_set_version"] = "0"
            old_markers[marker] = json.dumps(value)
            marker.write_text(old_markers[marker], encoding="utf-8")

        real_replace = Path.replace
        failing_directory = "models--qdrant--bge-small-en-v1.5-onnx-q"

        def fail_staging_publish(path: Path, target: Path):
            if path.name == failing_directory and path.parent.name.startswith(".wf-model-"):
                raise OSError("simulated publish failure")
            return real_replace(path, target)

        with patch.object(Path, "replace", fail_staging_publish):
            with self.assertRaisesRegex(OSError, "simulated publish failure"):
                model_bundle.materialize_bundle(bundle)
        for marker, expected in old_markers.items():
            self.assertEqual(marker.read_text(encoding="utf-8"), expected)

    def test_matching_model_set_asset_handoff_is_durable_across_upgrade_pause(self):
        feature = self.tmp / "wavefoundry-1.15.0.test.zip"
        with zipfile.ZipFile(feature, "w") as archive:
            archive.writestr(".wavefoundry/framework/VERSION", "1.15.0+test\n")
            archive.writestr(".wavefoundry/framework/scripts/model_bundle.py", 'MODEL_SET_VERSION = "1"\n')
        companion = self.tmp / "wavefoundry-models-1.zip"
        companion.write_bytes(b"model set")
        self.assertEqual(upgrade_wavefoundry._matching_model_bundle(feature), companion)
        handoff = upgrade_wavefoundry._model_bundle_lock_fields(feature, companion)
        self.assertEqual(handoff["model_bundle_path"], str(companion))
        self.assertEqual(handoff["model_bundle_model_set_version"], "1")

    def test_matching_model_set_asset_is_found_in_distribution_directory(self):
        feature = self.tmp / "wavefoundry-1.15.0.test.zip"
        with zipfile.ZipFile(feature, "w") as archive:
            archive.writestr(".wavefoundry/framework/scripts/model_bundle.py", 'MODEL_SET_VERSION = "2"\n')
        dist = self.tmp / "dist"
        dist.mkdir()
        companion = dist / "wavefoundry-models-2.zip"
        companion.write_bytes(b"model set")
        with patch.object(upgrade_wavefoundry, "_DIST_DIR", dist):
            self.assertEqual(upgrade_wavefoundry._matching_model_bundle(feature), companion)

    def test_find_local_bundle_uses_model_set_version_not_framework_version(self):
        dist = self.tmp / "dist"
        dist.mkdir()
        expected = dist / "wavefoundry-models-2.zip"
        expected.write_bytes(b"model set")
        self.assertEqual(model_bundle.find_local_bundle((dist,), "2"), expected)
        self.assertIsNone(model_bundle.find_local_bundle((dist,), "1"))


if __name__ == "__main__":
    unittest.main()
