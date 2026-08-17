import json
import ast
import hashlib
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
            # a non-ref member that carries whitespace at both ends: normalization must
            # NEVER touch it (real tokenizer.json files end in a newline)
            (base / "snapshots" / "rev" / "tokenizer.json").write_bytes(b" {}\n")
        self.out = self.tmp / "out"; self.out.mkdir()
        self.fast = self.tmp / "target-fast"
        self.onnx = self.tmp / "target-onnx"
        self.old_fast, self.old_onnx = os.environ.get("FASTEMBED_CACHE_PATH"), os.environ.get("WAVEFOUNDRY_ONNX_SRC_CACHE")
        os.environ["FASTEMBED_CACHE_PATH"] = str(self.fast)
        os.environ["WAVEFOUNDRY_ONNX_SRC_CACHE"] = str(self.onnx)
        self._real_load_manifest = model_bundle.load_canonical_verification_manifest
        self._test_manifest = model_bundle._manifest_from_cache(self.cache)
        self._manifest_patch = patch.object(
            model_bundle,
            "load_canonical_verification_manifest",
            side_effect=lambda path=None: self._test_manifest if path is None else self._real_load_manifest(path),
        )
        self._manifest_patch.start()

    def tearDown(self):
        self._manifest_patch.stop()
        if self.old_fast is None: os.environ.pop("FASTEMBED_CACHE_PATH", None)
        else: os.environ["FASTEMBED_CACHE_PATH"] = self.old_fast
        if self.old_onnx is None: os.environ.pop("WAVEFOUNDRY_ONNX_SRC_CACHE", None)
        else: os.environ["WAVEFOUNDRY_ONNX_SRC_CACHE"] = self.old_onnx
        shutil.rmtree(self.tmp)

    def test_checked_in_canonical_manifest_is_valid(self):
        self._manifest_patch.stop()
        manifest = model_bundle.load_canonical_verification_manifest()
        self.assertEqual(manifest["model_set_version"], model_bundle.MODEL_SET_VERSION)
        self.assertEqual(len(manifest["components"]), len(model_bundle.COMPONENTS))
        # Wave 1vglb: the CHECKED-IN manifest pins every refs/main at the 40-byte form
        # (sha256 of the bare revision), so the set-2 defect cannot be re-pinned by hand.
        import hashlib
        for component in manifest["components"]:
            refs = [f for f in component["files"] if f["path"].endswith("/refs/main")]
            self.assertEqual(len(refs), 1, component["id"])
            self.assertEqual(refs[0]["sha256"], hashlib.sha256(component["revision"].encode()).hexdigest(), component["id"])
            self.assertNotEqual(refs[0]["sha256"], hashlib.sha256((component["revision"] + "\n").encode()).hexdigest())

    def test_retired_model_residue_census_is_closed(self):
        """Legacy identities survive only in cleanup, comparison evidence, or history."""
        repo = SCRIPTS.parents[2]
        retired = ("BAAI", "arctic-embed-xs")

        production_hits: list[str] = []
        for path in sorted(SCRIPTS.rglob("*.py")):
            rel = path.relative_to(repo).as_posix()
            if "/tests/" in f"/{rel}" or "/benchmarks/" in f"/{rel}":
                continue
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if any(token in line for token in retired):
                    production_hits.append(f"{rel}:{number}:{line.strip()}")

        cleanup_source = (SCRIPTS / "upgrade_wavefoundry.py").read_text(encoding="utf-8")
        cleanup_tree = ast.parse(cleanup_source)
        allowlisted = {
            node.value
            for node in ast.walk(cleanup_tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and "BAAI" in node.value
        }
        self.assertTrue(allowlisted)
        self.assertTrue(all(hit.startswith(".wavefoundry/framework/scripts/upgrade_wavefoundry.py:")
                            and any(value in hit for value in allowlisted)
                            for hit in production_hits), production_hits)
        self.assertNotIn("arctic-embed-xs", cleanup_source)

        # 1v0r0 repair (F7): closed benchmark census. `benchmarks/` may carry
        # retired identifiers ONLY at the exact paths below, each covered by a
        # census class from the change doc's Requirement 7; any FUTURE
        # benchmark file naming a retired identifier fails here.
        bench_root = SCRIPTS / "benchmarks"
        bench_source = (bench_root / "embed_bench.py").read_text(encoding="utf-8")
        pinned_hashes = {
            node.targets[0].id: node.value.value
            for node in ast.parse(bench_source).body
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id
            in {"MODEL_SWAP_CODE_SHA256", "MODEL_SWAP_DOCS_SHA256"}
        }
        frozen_fixtures = {
            # Frozen comparison-input fixtures: authored at comparison time,
            # MAY name the then-current retired identifier in query or
            # accepted-answer text, hash-bound to the committed result,
            # never re-authored. The hash binding is enforced right here.
            "benchmarks/model_swap_code_queries.json": pinned_hashes[
                "MODEL_SWAP_CODE_SHA256"
            ],
            "benchmarks/model_swap_docs_queries.json": pinned_hashes[
                "MODEL_SWAP_DOCS_SHA256"
            ],
        }
        for rel, expected_sha in frozen_fixtures.items():
            digest = hashlib.sha256((SCRIPTS / rel).read_bytes()).hexdigest()
            self.assertEqual(digest, expected_sha, rel)
        benchmark_exemptions = set(frozen_fixtures) | {
            # The committed controlled-comparison result of those inputs.
            "benchmarks/model_swap_v2_result.json",
            # The comparison validator pins the retired side's provenance.
            "benchmarks/embed_bench.py",
            # Historical model-selection comparison evidence (pre-Arctic).
            "benchmarks/bench_report.json",
            "benchmarks/bench_report_final.json",
            "benchmarks/bench_report_sorted.json",
        }
        benchmark_hits: list[str] = []
        for path in sorted(bench_root.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(SCRIPTS).as_posix()
            if rel in benchmark_exemptions:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if any(token in text for token in retired):
                benchmark_hits.append(rel)
        self.assertEqual(benchmark_hits, [])

        test_hits: list[str] = []
        tests_root = SCRIPTS / "tests"
        for path in sorted(tests_root.rglob("*")):
            if not path.is_file() or path.suffix not in {".py", ".json"}:
                continue
            if path.name in {"test_upgrade_wavefoundry.py", "test_model_bundle.py"}:
                continue
            text = path.read_text(encoding="utf-8")
            if any(token in text for token in retired):
                test_hits.append(path.relative_to(repo).as_posix())
        self.assertEqual(test_hits, [])

        active_docs = [
            repo / "docs/architecture/current-state.md",
            repo / "docs/architecture/data-and-control-flow.md",
            repo / "docs/architecture/search-architecture.md",
            repo / "docs/architecture/testing-architecture.md",
            repo / "docs/architecture/chunking-and-indexing-pipeline.md",
            repo / "docs/architecture/performance-budget.md",
        ]
        for path in active_docs:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("BAAI/", text, path)
            self.assertNotIn("arctic-embed-xs", text, path)
            lowered = text.lower()
            self.assertTrue(
                "snowflake-arctic-embed-s" in lowered or "arctic embed s" in lowered,
                path,
            )

        embedding = (repo / "docs/architecture/embedding-model.md").read_text(encoding="utf-8")
        current, historical = embedding.split("### Historical:", 1)
        self.assertNotIn("BAAI/", current)
        self.assertNotIn("arctic-embed-xs", current)
        self.assertIn("BAAI/", historical)

    def test_bundle_refuses_cache_that_drifts_from_its_manifest_authority(self):
        source = self.cache / "fastembed" / "models--snowflake--snowflake-arctic-embed-s" / "snapshots" / "rev" / "onnx" / "model.onnx"
        source.write_bytes(b"drifted")
        with self.assertRaisesRegex(RuntimeError, "does not match the canonical"):
            model_bundle.build_bundle(self.out, cache_root=self.cache)

    def test_build_materialize_and_reuse(self):
        bundle = model_bundle.build_bundle(self.out, cache_root=self.cache)
        # Wave 1vglb: follow the live constant, not a literal set number.
        self.assertEqual(bundle.name, model_bundle.bundle_name())
        version = model_bundle.MODEL_SET_VERSION
        result = model_bundle.materialize_bundle(bundle, expected_model_set_version=version)
        self.assertEqual(result["published_components"], len(model_bundle.COMPONENTS))
        self.assertEqual(model_bundle.materialize_bundle(bundle, expected_model_set_version=version)["published_components"], 0)
        self.assertTrue((self.fast / "models--snowflake--snowflake-arctic-embed-s" / ".wavefoundry-model-bundle.json").is_file())

    # ------------------------------------------------------------------
    # Wave 1vglb (1vgla): refs/main normalization, the executed falsifications.
    # The fixture's cache deliberately writes ``refs/main`` as ``"rev\n"`` (the exact
    # defective 41-byte shape model set 2 shipped), so every test below runs against
    # the real known-bad input.
    # ------------------------------------------------------------------

    def _arctic_ref_member(self) -> str:
        return "models/onnx-src/models--Snowflake--snowflake-arctic-embed-s/refs/main"

    def test_build_normalizes_refs_main_and_manifest_pins_the_40_byte_form(self):
        # (a) build-side: the cache holds "rev\n"; the packed member and the
        # manifest sha must both describe the stripped form.
        import zipfile, hashlib
        on_disk = (self.cache / "onnx-src" / "models--Snowflake--snowflake-arctic-embed-s" / "refs" / "main").read_bytes()
        self.assertTrue(on_disk.endswith(b"\n"), "fixture must present the defective shape")
        bundle = model_bundle.build_bundle(self.out, cache_root=self.cache)
        with zipfile.ZipFile(bundle) as archive:
            packed = archive.read(self._arctic_ref_member())
        self.assertEqual(packed, b"rev")
        self.assertFalse(packed.endswith(b"\n"))
        shas = {f["path"]: f["sha256"] for c in self._test_manifest["components"] for f in c["files"]}
        pinned = shas[self._arctic_ref_member()]
        self.assertEqual(pinned, hashlib.sha256(b"rev").hexdigest())
        self.assertNotEqual(pinned, hashlib.sha256(b"rev\n").hexdigest())
        # normalization scope: a non-ref member keeps its whitespace, packed and pinned raw
        tok = self._arctic_ref_member().replace("refs/main", "snapshots/rev/tokenizer.json")
        with zipfile.ZipFile(bundle) as archive:
            self.assertEqual(archive.read(tok), b" {}\n")
        self.assertEqual(shas[tok], hashlib.sha256(b" {}\n").hexdigest())

    def test_materialize_writes_refs_main_normalized_even_from_a_newline_bundle(self):
        # (b) install-side, independent of build-side: hand-craft a bundle whose
        # packed refs/main carries the newline (as set 2 does) and prove the
        # installed file is the 40-byte form. Hash the manifest for the newline
        # form so the bundle passes verification the way set 2 would.
        import zipfile, json, hashlib, copy
        bundle = model_bundle.build_bundle(self.out, cache_root=self.cache)
        crafted = self.out / "crafted.zip"
        manifest = copy.deepcopy(self._test_manifest)
        for c in manifest["components"]:
            for f in c["files"]:
                if f["path"].endswith("refs/main"):
                    f["sha256"] = hashlib.sha256(b"rev\n").hexdigest()
        with zipfile.ZipFile(bundle) as src, zipfile.ZipFile(crafted, "w") as dst:
            for item in src.infolist():
                data = src.read(item.filename)
                if item.filename == model_bundle._MANIFEST_NAME:
                    data = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()
                elif item.filename.endswith("refs/main"):
                    data = b"rev\n"
                dst.writestr(item, data)
        with patch.object(model_bundle, "load_canonical_verification_manifest", side_effect=lambda path=None: manifest):
            # archive verification hashes the packed bytes as-is, so the newline form
            # matches this crafted manifest and the install path is reached
            model_bundle.materialize_bundle(crafted, expected_model_set_version=model_bundle.MODEL_SET_VERSION)
        arctic = self.onnx / "models--Snowflake--snowflake-arctic-embed-s"
        installed = (arctic / "refs" / "main").read_bytes()
        self.assertEqual(installed, b"rev", "install must write the normalized 40-byte form")
        self.assertEqual((arctic / "snapshots" / "rev" / "tokenizer.json").read_bytes(), b" {}\n",
                         "non-ref members install byte-identically")

    def test_known_bad_pair_newline_ref_misses_main_and_normalized_resolves(self):
        # (d) the executed known-bad from the 1.16.4 diagnosis, on a fixture cache:
        # huggingface_hub resolves ``main`` by reading refs/main VERBATIM.
        try:
            from huggingface_hub import try_to_load_from_cache
        except Exception:  # pragma: no cover
            self.skipTest("huggingface_hub unavailable")
        repo_dir = self.tmp / "hfcache" / "models--Snowflake--snowflake-arctic-embed-s"
        snap = repo_dir / "snapshots" / "abcdef1234567890abcdef1234567890abcdef12"
        (snap / "onnx").mkdir(parents=True)
        (snap / "onnx" / "model.onnx").write_bytes(b"w")
        (repo_dir / "refs").mkdir()
        (repo_dir / "refs" / "main").write_bytes(b"abcdef1234567890abcdef1234567890abcdef12\n")
        cache_dir = str(self.tmp / "hfcache")
        before = try_to_load_from_cache("Snowflake/snowflake-arctic-embed-s", "onnx/model.onnx", cache_dir=cache_dir, revision="main")
        self.assertIsNone(before, "newline ref must fail to resolve main (the known-bad)")
        (repo_dir / "refs" / "main").write_bytes(model_bundle._normalized_ref_bytes(b"abcdef1234567890abcdef1234567890abcdef12\n"))
        after = try_to_load_from_cache("Snowflake/snowflake-arctic-embed-s", "onnx/model.onnx", cache_dir=cache_dir, revision="main")
        self.assertTrue(isinstance(after, str) and after.endswith("model.onnx"), "normalized ref must resolve main")

    def test_legacy_marker_with_verbatim_ref_digest_still_verifies(self):
        # Markers written before 1vglb pinned the ref's VERBATIM digest (set 2 shipped a
        # 41-byte ref). The normalizing verifier must still accept them, so an installed
        # set 2 reads as an older managed set rather than a mixed cache during upgrade.
        import hashlib, json
        dest = self.cache / "onnx-src" / "models--Snowflake--snowflake-arctic-embed-s"
        legacy = {
            "files": {
                "refs/main": hashlib.sha256(b"rev\n").hexdigest(),
                "snapshots/rev/onnx/model.onnx": hashlib.sha256(b"models--Snowflake--snowflake-arctic-embed-s").hexdigest(),
                "snapshots/rev/tokenizer.json": hashlib.sha256(b" {}\n").hexdigest(),
            },
            "model_set_version": "2",
            "fingerprint": model_bundle.EMBEDDING_COMPATIBILITY_FINGERPRINT,
        }
        marker = self.tmp / "legacy-marker.json"
        marker.write_text(json.dumps(legacy), encoding="utf-8")
        self.assertIsNotNone(model_bundle._verified_marker(dest, marker))
        # a normalized (post-1vglb) marker verifies too, and a tampered ref still fails
        legacy["files"]["refs/main"] = hashlib.sha256(b"rev").hexdigest()
        marker.write_text(json.dumps(legacy), encoding="utf-8")
        self.assertIsNotNone(model_bundle._verified_marker(dest, marker))
        legacy["files"]["refs/main"] = hashlib.sha256(b"other").hexdigest()
        marker.write_text(json.dumps(legacy), encoding="utf-8")
        self.assertIsNone(model_bundle._verified_marker(dest, marker))
        # and a non-ref member never gets the legacy tolerance
        legacy["files"]["refs/main"] = hashlib.sha256(b"rev").hexdigest()
        legacy["files"]["snapshots/rev/tokenizer.json"] = hashlib.sha256(b"{}").hexdigest()
        marker.write_text(json.dumps(legacy), encoding="utf-8")
        self.assertIsNone(model_bundle._verified_marker(dest, marker))

    def test_set3_keeps_the_set2_embedding_fingerprint(self):
        # The identity decision, pinned: a set bump that changes only a reference
        # byte must not invalidate any existing index.
        self.assertEqual(model_bundle.MODEL_SET_VERSION, "3")
        self.assertEqual(model_bundle.EMBEDDING_COMPATIBILITY_FINGERPRINT, "wf-model-set-2-20260811-arctic-s")

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

    def test_rejects_self_consistent_substitute_before_cache_publication(self):
        """An internally valid rehash/revision is still not the installed canonical set."""
        bundle = model_bundle.build_bundle(self.out, cache_root=self.cache)
        model_bundle.materialize_bundle(bundle)
        installed = (
            self.fast
            / "models--snowflake--snowflake-arctic-embed-s"
            / "snapshots"
            / "rev"
            / "onnx"
            / "model.onnx"
        )
        before_payload = installed.read_bytes()
        before_marker = (installed.parents[3] / ".wavefoundry-model-bundle.json").read_bytes()

        substitute = self.out / "self-consistent-substitute.zip"
        with zipfile.ZipFile(bundle) as source:
            members = {info.filename: source.read(info.filename) for info in source.infolist()}
        manifest = json.loads(members["model-bundle-manifest.json"])
        component = next(item for item in manifest["components"] if item["target"] == "fastembed")
        payload_name = next(
            item["path"] for item in component["files"] if item["path"].endswith("onnx/model.onnx")
        )
        ref_name = next(
            item["path"] for item in component["files"] if item["path"].endswith("refs/main")
        )
        members[payload_name] = b"self-consistent replacement payload"
        members[ref_name] = b"substitute-revision\n"
        component["revision"] = "substitute-revision"
        for item in component["files"]:
            if item["path"] in {payload_name, ref_name}:
                item["sha256"] = model_bundle._sha256(members[item["path"]])
        members["model-bundle-manifest.json"] = (
            json.dumps(manifest, sort_keys=True, indent=2) + "\n"
        ).encode("utf-8")
        with zipfile.ZipFile(substitute, "w", compression=zipfile.ZIP_DEFLATED) as target:
            for name, data in members.items():
                target.writestr(name, data)

        with self.assertRaisesRegex(RuntimeError, "does not match the installed canonical"):
            model_bundle.materialize_bundle(substitute)
        self.assertEqual(installed.read_bytes(), before_payload)
        self.assertEqual((installed.parents[3] / ".wavefoundry-model-bundle.json").read_bytes(), before_marker)

    def test_rejects_model_set_version_mismatch(self):
        bundle = model_bundle.build_bundle(self.out, cache_root=self.cache)
        with self.assertRaisesRegex(RuntimeError, "does not match"):
            model_bundle.materialize_bundle(bundle, expected_model_set_version="9.9.9")

    def test_repairs_corrupt_cache(self):
        bundle = model_bundle.build_bundle(self.out, cache_root=self.cache)
        model_bundle.materialize_bundle(bundle)
        cached = self.fast / "models--snowflake--snowflake-arctic-embed-s" / "snapshots" / "rev" / "onnx" / "model.onnx"
        cached.write_bytes(b"corrupt")
        self.assertEqual(model_bundle.materialize_bundle(bundle)["published_components"], 1)

    def test_current_set_replaces_v1_and_does_not_downgrade_newer_marker(self):
        bundle = model_bundle.build_bundle(self.out, cache_root=self.cache)
        model_bundle.materialize_bundle(bundle)
        for _id, target, directory, _license, _upstream in model_bundle.COMPONENTS:
            marker = model_bundle._target_root(target) / directory / ".wavefoundry-model-bundle.json"
            value = json.loads(marker.read_text(encoding="utf-8"))
            value["model_set_version"] = "1"
            marker.write_text(json.dumps(value), encoding="utf-8")
        self.assertEqual(model_bundle.materialize_bundle(bundle)["published_components"], len(model_bundle.COMPONENTS))
        for _id, target, directory, _license, _upstream in model_bundle.COMPONENTS:
            marker = model_bundle._target_root(target) / directory / ".wavefoundry-model-bundle.json"
            value = json.loads(marker.read_text(encoding="utf-8"))
            value["model_set_version"] = "3"
            marker.write_text(json.dumps(value), encoding="utf-8")
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
        failing_directory = "models--snowflake--snowflake-arctic-embed-s"

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

    def test_manual_recovery_guidance_uses_exact_asset_and_standard_locations(self):
        guidance = model_bundle.manual_recovery_guidance("2")
        self.assertIn("wavefoundry-models-2.zip", guidance)
        self.assertIn("same Wavefoundry release", guidance)
        self.assertIn("target repository root, ~/", guidance)
        self.assertIn("~/.wavefoundry/", guidance)
        self.assertIn("~/.wavefoundry/dist/", guidance)
        self.assertIn("~/Downloads/", guidance)
        self.assertIn("leave it zipped", guidance)
        self.assertIn("leaves the verified cache unchanged", guidance)

    def test_attests_complete_online_cache_from_verification_manifest(self):
        bundle = model_bundle.build_bundle(self.out, cache_root=self.cache)
        with zipfile.ZipFile(bundle) as archive:
            manifest_path = self.out / "verification.json"
            manifest_path.write_bytes(archive.read("model-bundle-manifest.json"))
        for _id, target, directory, _license, _upstream in model_bundle.COMPONENTS:
            shutil.copytree(self.cache / target / directory, model_bundle._target_root(target) / directory)

        self.assertTrue(model_bundle.attest_online_cache(manifest_path))
        self.assertEqual(model_bundle.local_model_set_status(), "current")
        for _id, target, directory, _license, _upstream in model_bundle.COMPONENTS:
            self.assertTrue((model_bundle._target_root(target) / directory / ".wavefoundry-model-bundle.json").is_file())

    def test_attest_normalizes_legacy_refs_in_place_and_materialize_skip_repairs_them(self):
        # F-1vglb-03: a legacy set-2 cache (41-byte ref) upgraded WITHOUT the asset in reach
        # must not be relabeled with the defect intact. Attest normalizes the bytes it
        # attests; the already-installed skip in materialize repairs them too; and main
        # resolves under the REAL huggingface_hub afterwards.
        try:
            from huggingface_hub import try_to_load_from_cache
        except Exception:  # pragma: no cover
            self.skipTest("huggingface_hub unavailable")
        bundle = model_bundle.build_bundle(self.out, cache_root=self.cache)
        with zipfile.ZipFile(bundle) as archive:
            manifest_path = self.out / "verification.json"
            manifest_path.write_bytes(archive.read("model-bundle-manifest.json"))
        for _id, target, directory, _license, _upstream in model_bundle.COMPONENTS:
            shutil.copytree(self.cache / target / directory, model_bundle._target_root(target) / directory)
        arctic = self.onnx / "models--Snowflake--snowflake-arctic-embed-s"
        ref = arctic / "refs" / "main"
        self.assertEqual(ref.read_bytes(), b"rev\n", "fixture premise: the legacy 41-byte shape")
        # 1) attest with no asset in reach: attested AND normalized
        self.assertTrue(model_bundle.attest_online_cache(manifest_path))
        self.assertEqual(ref.read_bytes(), b"rev")
        for _id, target, directory, _license, _upstream in model_bundle.COMPONENTS:
            self.assertEqual((model_bundle._target_root(target) / directory / "refs" / "main").read_bytes(), b"rev")
        self.assertEqual(model_bundle.local_model_set_status(), "current")
        # 2) an attested marker with a defective ref left behind by older code: the asset drop
        #    is still a no-op publish, but the skip path repairs the bytes
        ref.write_bytes(b"rev\n")
        result = model_bundle.materialize_bundle(bundle, expected_model_set_version=model_bundle.MODEL_SET_VERSION)
        self.assertEqual(result["published_components"], 0)
        self.assertEqual(ref.read_bytes(), b"rev")
        # 3) the runtime resolves main offline against the normalized ref
        hit = try_to_load_from_cache("Snowflake/snowflake-arctic-embed-s", "onnx/model.onnx", cache_dir=str(self.onnx), revision="main")
        self.assertTrue(isinstance(hit, str) and hit.endswith("model.onnx"))

    def test_normalize_refs_in_place_touches_only_defective_refs_and_reports_originals(self):
        dest = self.cache / "onnx-src" / "models--Snowflake--snowflake-arctic-embed-s"
        (dest / "refs" / "other").write_bytes(b"abc")
        changed = model_bundle._normalize_refs_in_place(dest)
        self.assertEqual([(p.name, o) for p, o in changed], [("main", b"rev\n")])
        self.assertEqual((dest / "refs" / "main").read_bytes(), b"rev")
        self.assertEqual((dest / "refs" / "other").read_bytes(), b"abc")
        self.assertEqual((dest / "snapshots" / "rev" / "tokenizer.json").read_bytes(), b" {}\n", "never touches non-refs")
        self.assertEqual(model_bundle._normalize_refs_in_place(dest), [], "idempotent")
        self.assertEqual(model_bundle._normalize_refs_in_place(self.tmp / "no-such"), [])

    def test_refuses_incomplete_or_extra_online_cache_without_markers(self):
        bundle = model_bundle.build_bundle(self.out, cache_root=self.cache)
        with zipfile.ZipFile(bundle) as archive:
            manifest_path = self.out / "verification.json"
            manifest_path.write_bytes(archive.read("model-bundle-manifest.json"))
        for _id, target, directory, _license, _upstream in model_bundle.COMPONENTS:
            shutil.copytree(self.cache / target / directory, model_bundle._target_root(target) / directory)
        extra = self.fast / "models--snowflake--snowflake-arctic-embed-s" / "snapshots" / "rev" / "extra.bin"
        extra.write_bytes(b"unexpected")

        self.assertFalse(model_bundle.attest_online_cache(manifest_path))
        self.assertEqual(model_bundle.local_model_set_status(), "unmanaged")

    def test_missing_verification_manifest_is_a_nonfatal_noop(self):
        self.assertFalse(model_bundle.attest_online_cache(self.out / "missing.json"))


if __name__ == "__main__":
    unittest.main()
