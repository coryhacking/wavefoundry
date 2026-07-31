#!/usr/bin/env python3
from __future__ import annotations

import json
import contextlib
import io
import shutil
import shlex
import subprocess
import sys
import tempfile
import types
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_pack
import dashboard_lib
import lifecycle_lock
import review_evidence
import upgrade_bridge_bootstrap
import upgrade_bundle
import upgrade_extensions
import upgrade_protocol


class UpgradeProtocolTests(unittest.TestCase):
    def _feature(self, root: Path) -> Path:
        fw = root / ".wavefoundry/framework"
        (fw / "scripts").mkdir(parents=True)
        for source in SCRIPTS.glob("*.py"):
            shutil.copy2(source, fw / "scripts" / source.name)
        (fw / "VERSION").write_text("1.15.0+test\n", encoding="utf-8")
        return build_pack.build_zip(
            root,
            "1.15.0",
            "test",
            framework_dir=fw,
            write_version=False,
            update_manifest=False,
            inject_install_templates=False,
        )

    def test_feature_metadata_and_exact_protocol_mappings(self):
        with tempfile.TemporaryDirectory() as tmp:
            feature = self._feature(Path(tmp))
            metadata = upgrade_protocol.read_pack_protocol(feature)
            self.assertEqual(metadata["artifact_type"], "feature")
            self.assertEqual(upgrade_protocol.runner_compatibility(1, metadata), "legacy_optional_extension")
            self.assertEqual(upgrade_protocol.runner_compatibility(2, metadata), "compatible")
            for bad in (0, 3, "2"):
                with self.subTest(bad=bad), self.assertRaises(upgrade_protocol.UpgradeProtocolError):
                    upgrade_protocol.runner_compatibility(bad, metadata)

    def test_missing_malformed_and_decreasing_metadata_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing = root / "missing.zip"
            with zipfile.ZipFile(missing, "w") as archive:
                archive.writestr("x", "x")
            with self.assertRaisesRegex(upgrade_protocol.UpgradeProtocolError, "unavailable"):
                upgrade_protocol.read_pack_protocol(missing)
            malformed = root / "malformed.zip"
            with zipfile.ZipFile(malformed, "w") as archive:
                archive.writestr(upgrade_protocol.PROTOCOL_METADATA_ARCNAME, "{")
            with self.assertRaisesRegex(upgrade_protocol.UpgradeProtocolError, "malformed"):
                upgrade_protocol.read_pack_protocol(malformed)
            value = upgrade_protocol.build_protocol_metadata(
                release_version="1.15.0+x", build_id="x", artifact_type="feature"
            )
            for minimum in (1, 3):
                with self.subTest(minimum=minimum):
                    value["minimum_runner_protocol"] = minimum
                    with self.assertRaisesRegex(upgrade_protocol.UpgradeProtocolError, "unsupported or decreasing"):
                        upgrade_protocol.validate_protocol_metadata(value)

    def test_mandatory_feature_code_fails_closed_before_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            feature = self._feature(root)
            upgrade_protocol.validate_feature_pack(feature)
            for filename, replacement, message in (
                ("publication_control.py", None, "missing"),
                ("upgrade_extensions.py", "def broken(:\n", "not importable"),
                ("review_policy_upgrade.py", "import not_in_the_pack\n", "unavailable import"),
            ):
                with self.subTest(filename=filename):
                    mutated = root / f"mutated-{filename}.zip"
                    with zipfile.ZipFile(feature, "r") as source, zipfile.ZipFile(mutated, "w") as target:
                        for info in source.infolist():
                            if info.filename.endswith("/" + filename):
                                if replacement is not None:
                                    target.writestr(info, replacement)
                                continue
                            target.writestr(info, source.read(info.filename))
                    with self.assertRaisesRegex(upgrade_protocol.UpgradeProtocolError, message):
                        upgrade_protocol.validate_feature_pack(mutated)

    def test_mandatory_feature_code_must_import_and_declare_protocol_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            feature = self._feature(root)
            for filename, transform, message in (
                (
                    "review_policy_upgrade.py",
                    lambda source: source.replace(
                        "from __future__ import annotations\n",
                        "from __future__ import annotations\n\n"
                        "raise RuntimeError('import boom')\n",
                        1,
                    ),
                    "not importable",
                ),
                (
                    "upgrade_protocol.py",
                    lambda source: source.replace(
                        "UPGRADE_PROTOCOL_VERSION = 2",
                        "UPGRADE_PROTOCOL_VERSION = 999",
                    ),
                    "declarations do not match protocol 2",
                ),
            ):
                with self.subTest(filename=filename):
                    mutated = root / f"import-{filename}.zip"
                    with zipfile.ZipFile(feature, "r") as source, zipfile.ZipFile(mutated, "w") as target:
                        for info in source.infolist():
                            body = source.read(info.filename)
                            if info.filename.endswith("/" + filename):
                                body = transform(body.decode("utf-8")).encode("utf-8")
                            target.writestr(info, body)
                    with self.assertRaisesRegex(upgrade_protocol.UpgradeProtocolError, message):
                        upgrade_protocol.validate_feature_pack(mutated)

    def test_supported_floor_hook_refuses_feature_before_extract(self):
        with tempfile.TemporaryDirectory() as tmp:
            feature = self._feature(Path(tmp))
            ctx = type("LegacyContext", (), {"zip_path": feature})()
            output = io.StringIO()
            with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as raised:
                upgrade_extensions.post_preflight(ctx)
            self.assertEqual(raised.exception.code, 3)
            payload = json.loads(output.getvalue())
            self.assertEqual(payload["code"], "bridge_release_required")
            self.assertEqual(payload["runner_protocol"], 1)
            self.assertEqual(payload["package"], str(feature))
            self.assertTrue(payload["package_present"])
            self.assertEqual(payload["command_argv"][1], str(feature))
            self.assertIn("Wavefoundry dashboard and MCP server", payload["hosts_to_stop"])
            self.assertIn("keep the agent session idle", payload["hosts_to_stop"])
            self.assertIn("ordinary non-MCP shell", payload["restart_guidance"])
            self.assertIn("restart every attached host", payload["restart_guidance"])
            self.assertIn(
                "already-loaded protocol-1 MCP wrapper",
                payload["legacy_wrapper_limitation"],
            )
            self.assertIn(
                "operator does not enter a command",
                payload["legacy_wrapper_limitation"],
            )

    def test_public_bridge_carriers_assign_agent_shell_and_multihost_restart(self):
        repo_root = SCRIPTS.parents[2]
        carriers = (
            repo_root / "README.md",
            repo_root / ".wavefoundry/README.md",
            repo_root / ".wavefoundry/framework/install/install-block.md",
            repo_root / "docs/agents/personas/framework-operator.md",
        )
        for carrier in carriers:
            with self.subTest(carrier=carrier):
                text = carrier.read_text(encoding="utf-8")
                normalized = " ".join(text.split())
                self.assertIn("ordinary non-MCP shell", normalized)
                self.assertIn("operator does not copy or type", normalized)
                self.assertIn("restart every attached host", normalized.lower())

    def test_handoff_command_rendering_keeps_structured_argv_authoritative(self):
        fixtures = (
            ["python3", "/tmp/Üpgrade package.zip", "--root", "/tmp/repo space"],
            ["python.exe", r"C:\Users\A Name\package.zip", "--root", r"C:\work\repo"],
            ["python3", "/mnt/c/Users/A Name/package.zip", "--root", "/mnt/c/work/repo"],
        )
        for argv in fixtures:
            with self.subTest(argv=argv):
                original = list(argv)
                posix = upgrade_extensions._render_command(argv, platform_name="posix")
                windows = upgrade_extensions._render_command(argv, platform_name="nt")
                self.assertEqual(shlex.split(posix), argv)
                self.assertTrue(posix)
                self.assertTrue(windows)
                self.assertEqual(argv, original, "rendering must not mutate argv authority")

    def test_windows_handoff_uses_console_python_not_pythonw(self):
        pythonw = r"C:\Wavefoundry\venv\Scripts\pythonw.exe"
        self.assertEqual(
            upgrade_extensions._operator_python(pythonw, platform_name="nt"),
            r"C:\Wavefoundry\venv\Scripts\python.exe",
        )
        python = r"C:\Wavefoundry\venv\Scripts\python.exe"
        self.assertEqual(
            upgrade_extensions._operator_python(python, platform_name="nt"), python
        )
        self.assertEqual(
            upgrade_extensions._operator_python("/usr/bin/python3", platform_name="posix"),
            "/usr/bin/python3",
        )

    def test_public_windows_refusal_payload_uses_console_python(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            feature = self._feature(root)
            ctx = type("LegacyContext", (), {"zip_path": feature, "root": root})()
            output = io.StringIO()
            operator_python = upgrade_extensions._operator_python
            with patch.object(
                upgrade_extensions.sys,
                "executable",
                r"C:\Wavefoundry\venv\Scripts\pythonw.exe",
            ), patch.object(
                upgrade_extensions,
                "_operator_python",
                side_effect=lambda executable: operator_python(
                    executable, platform_name="nt"
                ),
            ), contextlib.redirect_stdout(output), self.assertRaises(SystemExit):
                upgrade_extensions.post_preflight(ctx)
            payload = json.loads(output.getvalue())
            self.assertTrue(payload["package_present"])
            self.assertEqual(payload["package"], str(feature))
            self.assertEqual(
                payload["command_argv"][0],
                r"C:\Wavefoundry\venv\Scripts\python.exe",
            )

    def test_builder_bundle_contains_exact_selected_archives(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            feature = self._feature(root)
            artifacts = build_pack.build_protocol_bridge_artifacts(
                feature, version="1.15.0", build_prefix="bundle",
                bootstrap_source=SCRIPTS / "upgrade_bridge_bootstrap.py",
            )
            feature_payload = feature.read_bytes()
            bridge_name = artifacts["bridge"].name
            bridge_payload = artifacts["bridge"].read_bytes()
            selection_name = artifacts["selection"].name
            selection_payload = artifacts["selection"].read_bytes()
            bundle = build_pack.build_upgrade_bundle(
                feature, artifacts, version="1.15.0", build_prefix="bundle",
                bundle_source=SCRIPTS / "upgrade_bundle.py",
            )
            self.assertEqual(bundle, feature)
            with zipfile.ZipFile(bundle, "r") as archive:
                self.assertEqual(
                    archive.read("payload/" + feature.name), feature_payload
                )
                self.assertEqual(
                    archive.read("payload/" + bridge_name), bridge_payload,
                )
                self.assertEqual(
                    archive.read("payload/" + selection_name), selection_payload,
                )
                self.assertIn(
                    ".wavefoundry/framework/UPGRADE-PROTOCOL.json", archive.namelist()
                )
                self.assertIn("__main__.py", archive.namelist())
                self.assertIn("upgrade_bridge_bootstrap.py", archive.namelist())
                self.assertIn("subprocess_util.py", archive.namelist())
            self.assertFalse(any(path.exists() for path in artifacts.values()))
            self.assertEqual(list(root.glob("wavefoundry-*")), [feature])
            refused = subprocess.run(
                [sys.executable, str(bundle), "--root", str(root / "target")],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            self.assertEqual(refused.returncode, 2, refused.stderr)
            self.assertEqual(
                json.loads(refused.stdout)["code"], "host_quiescence_required"
            )

    def test_bundle_refuses_before_materialization_without_confirmation(self):
        with patch.object(
            upgrade_bridge_bootstrap,
            "install",
            side_effect=AssertionError("install/materialization must not run"),
        ):
            with self.assertRaisesRegex(
                upgrade_bridge_bootstrap.BridgeError, "host_quiescence_required"
            ):
                upgrade_bundle.run(Path("missing.pyz"), Path("missing-root"), hosts_stopped=False)

    def test_bundle_rejects_cross_platform_payload_traversal_before_writes(self):
        bad_names = (
            r"payload/..\framework\VERSION",
            r"payload/C:\outside\feature.zip",
        )
        for index, bad_name in enumerate(bad_names):
            with self.subTest(name=bad_name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                bundle = root / f"bad-{index}.pyz"
                with zipfile.ZipFile(bundle, "w") as archive:
                    archive.writestr("__main__.py", "")
                    archive.writestr("upgrade_bridge_bootstrap.py", "")
                    archive.writestr("subprocess_util.py", "")
                    archive.writestr(bad_name, "payload")
                destination = root / "materialized"
                destination.mkdir()
                with self.assertRaisesRegex(
                    upgrade_bridge_bootstrap.BridgeError, "payload paths are malformed"
                ):
                    upgrade_bundle._materializer(bundle)(destination)
                self.assertEqual(list(destination.iterdir()), [])
        self.assertTrue(upgrade_bundle._safe_payload_name("payload/feature.zip"))

    def test_spawn_failure_after_bridge_swap_returns_bounded_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".wavefoundry").mkdir()
            bridge = {
                "status": "bridge_installed",
                "source_version": "1.14.0",
                "source_protocol": 1,
                "target_version": "1.15.0",
                "target_protocol": 2,
                "rollback": str(root / ".wavefoundry/framework.rollback-test"),
                "next_argv": ["python.exe", "runner.py", "--yes"],
            }
            with patch.object(
                upgrade_bridge_bootstrap, "install", return_value=bridge
            ), patch.object(
                upgrade_bundle.subprocess_util,
                "isolated_run",
                side_effect=OSError("cannot spawn"),
            ):
                code, payload = upgrade_bundle.run(
                    root / "bundle.pyz", root, hosts_stopped=True
                )
            self.assertEqual(code, 2)
            self.assertEqual(payload["feature_state"], "spawn_failed")
            self.assertEqual(payload["rollback"], bridge["rollback"])
            self.assertEqual(payload["recovery"]["argv"], bridge["next_argv"])
            instruction = payload["recovery"]["instruction"]
            self.assertIn("agent execute the exact recovery argv", instruction)
            self.assertIn("ordinary non-MCP shell", instruction)
            self.assertIn("operator does not copy or type", instruction)
            self.assertIn("Restart every attached host", instruction)
            self.assertIn("cannot spawn", payload["stderr"])

    def test_primary_success_recovery_names_reconciliation_cleanup_and_audit(self):
        recovery = upgrade_bundle._recovery(
            Path("/repo"), {"next_argv": []}, "primary_phase_complete"
        )
        self.assertEqual(recovery["kind"], "restart_reconcile_then_cleanup")
        instruction = recovery["instruction"]
        self.assertIn("Restart every attached agent/MCP host", instruction)
        self.assertIn("reconciliation/editing pass", instruction)
        self.assertIn("wf_upgrade(phase='cleanup')", instruction)
        self.assertIn("wf_audit", instruction)

    def test_memory_pause_recovery_requires_every_attached_host_restart(self):
        recovery = upgrade_bundle._recovery(
            Path("/repo"), {"next_argv": []}, "awaiting_memory_validation"
        )
        self.assertEqual(recovery["kind"], "restart_then_resume_memory")
        self.assertIn(
            "Restart every attached agent/MCP host",
            recovery["instruction"],
        )
        self.assertIn("resume_after_memory", recovery["instruction"])

    def test_retained_checkpoint_recovery_assigns_agent_shell_and_multihost_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            recovery = upgrade_bundle._recovery(
                Path(tmp),
                {"next_argv": ["python3", "runner.py", "--yes"]},
                "failed",
            )
        self.assertEqual(recovery["kind"], "retained_checkpoint")
        instruction = recovery["instruction"]
        self.assertIn("agent execute the exact recovery argv", instruction)
        self.assertIn("ordinary non-MCP shell", instruction)
        self.assertIn("operator does not copy or type", instruction)
        self.assertIn("Restart every attached host", instruction)

    def test_bundle_validation_failure_cleans_composition_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            feature = self._feature(root)
            artifacts = build_pack.build_protocol_bridge_artifacts(
                feature,
                version="1.15.0",
                build_prefix="cleanup",
                bootstrap_source=SCRIPTS / "upgrade_bridge_bootstrap.py",
            )
            artifact_paths = tuple(artifacts.values())
            with feature.open("ab") as handle:
                handle.write(b"tampered")

            with self.assertRaisesRegex(
                RuntimeError,
                "feature artifact no longer matches",
            ):
                build_pack.build_upgrade_bundle(
                    feature,
                    artifacts,
                    version="1.15.0",
                    build_prefix="cleanup",
                    bundle_source=SCRIPTS / "upgrade_bundle.py",
                )

            self.assertTrue(feature.is_file())
            self.assertTrue(all(not path.exists() for path in artifact_paths))

    def test_bundle_executes_hash_pinned_feature_once_and_reports_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".wavefoundry").mkdir()
            bridge = {
                "status": "bridge_installed",
                "source_version": "1.14.0",
                "source_protocol": 1,
                "target_version": "1.15.0",
                "target_protocol": 2,
                "rollback": str(root / ".wavefoundry/framework.rollback-test"),
                "next_argv": [sys.executable, "runner.py", "--pack", "exact.zip", "--yes"],
            }
            completed = type(
                "Completed", (), {"returncode": 4, "stdout": "paused", "stderr": ""}
            )()
            with patch.object(
                upgrade_bridge_bootstrap, "install", return_value=bridge
            ) as install_call, patch.object(
                upgrade_bundle.subprocess_util, "isolated_run", return_value=completed
            ) as run_call:
                code, payload = upgrade_bundle.run(
                    root / "bundle.pyz", root, hosts_stopped=True
                )
            self.assertEqual(code, 4)
            install_call.assert_called_once()
            run_call.assert_called_once()
            self.assertEqual(run_call.call_args.args[0], bridge["next_argv"])
            self.assertEqual(payload["feature_state"], "awaiting_memory_validation")
            self.assertEqual(payload["recovery"]["kind"], "restart_then_resume_memory")
            self.assertTrue(payload["restart_required"])

    def test_real_bundle_crosses_bridge_and_invokes_installed_feature_runner(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            feature = self._feature(root)
            artifacts = build_pack.build_protocol_bridge_artifacts(
                feature, version="1.15.0", build_prefix="rehearsal",
                bootstrap_source=SCRIPTS / "upgrade_bridge_bootstrap.py",
            )
            bundle = build_pack.build_upgrade_bundle(
                feature, artifacts, version="1.15.0", build_prefix="rehearsal",
                bundle_source=SCRIPTS / "upgrade_bundle.py",
            )
            target = root / "tagged 1.14 fixture"
            framework = target / ".wavefoundry/framework"
            framework.mkdir(parents=True)
            (framework / "VERSION").write_text("1.14.0\n", encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(bundle),
                    "--root",
                    str(target),
                    "--confirm-hosts-stopped",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=60,
                check=False,
            )
            payload = json.loads(completed.stdout.splitlines()[-1])
            self.assertEqual(payload["bridge_state"], "bridge_installed")
            self.assertEqual(payload["source_version"], "1.14.0")
            self.assertEqual(payload["target_version"], "1.15.0")
            self.assertIn(payload["feature_exit_code"], (0, 1, 2, 3, 4))
            self.assertTrue(payload["restart_required"])
            self.assertTrue((framework / "UPGRADE-PROTOCOL.json").is_file())
            retained = target / ".wavefoundry/upgrade-assets" / feature.name
            with zipfile.ZipFile(feature, "r") as package:
                feature_payload = package.read("payload/" + feature.name)
            self.assertEqual(retained.read_bytes(), feature_payload)

    def test_real_builder_emits_framework_only_bridge_and_verified_bootstrap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            feature = self._feature(root)
            artifacts = build_pack.build_protocol_bridge_artifacts(
                feature,
                version="1.15.0",
                build_prefix="test",
                bootstrap_source=SCRIPTS / "upgrade_bridge_bootstrap.py",
            )
            self.assertNotEqual(artifacts["bridge"], feature)
            selection = json.loads(artifacts["selection"].read_text("utf-8"))
            self.assertNotEqual(selection["bridge_build_id"], "test")
            self.assertEqual(selection["supported_source_version"], "1.14.0")
            self.assertEqual(selection["supported_source_protocol"], 1)
            self.assertEqual(selection["feature_release_version"], "1.15.0")
            with zipfile.ZipFile(artifacts["bridge"], "r") as archive:
                names = archive.namelist()
                self.assertTrue(names)
                self.assertTrue(all(name.startswith(".wavefoundry/framework/") for name in names))
                self.assertNotIn("install-wavefoundry.md", names)
                self.assertEqual(
                    archive.read(".wavefoundry/framework/VERSION"),
                    b"protocol-bridge-2\n",
                )

            target = root / "target with spaces"
            current = target / ".wavefoundry/framework"
            current.mkdir(parents=True)
            (current / "old.txt").write_text("old\n", encoding="utf-8")
            (current / "VERSION").write_text("1.14.0\n", encoding="utf-8")
            result = upgrade_bridge_bootstrap.install(
                target,
                artifacts["selection"],
                hosts_stopped=True,
            )
            self.assertEqual(result["status"], "bridge_installed")
            self.assertTrue((current / "UPGRADE-PROTOCOL.json").is_file())
            self.assertTrue(Path(result["rollback"]).joinpath("old.txt").is_file())
            self.assertIn("--pack", result["next_command"])
            self.assertIn("--expected-pack-sha256", result["next_argv"])
            self.assertIn("--yes", result["next_argv"])
            self.assertTrue(Path(result["feature_archive"]).is_file())
            if sys.platform != "win32":
                self.assertEqual(shlex.split(result["next_command"]), result["next_argv"])
            self.assertEqual((current / "VERSION").read_text("utf-8"), "1.14.0\n")
            rollback_record = json.loads((current / "BRIDGE-ROLLBACK.json").read_text("utf-8"))
            self.assertTrue(rollback_record["hosts_stopped_confirmed"])

    def test_bridge_rejects_wrong_or_already_upgraded_source_before_staging(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            feature = self._feature(root)
            artifacts = build_pack.build_protocol_bridge_artifacts(
                feature, version="1.15.0", build_prefix="identity",
                bootstrap_source=SCRIPTS / "upgrade_bridge_bootstrap.py",
            )
            for installed, protocol, message in (
                ("9.9.9", None, "requires installed source version"),
                ("1.14.0", 2, "already uses protocol 2"),
            ):
                with self.subTest(installed=installed, protocol=protocol):
                    target = root / f"target-{installed}-{protocol}"
                    current = target / ".wavefoundry/framework"
                    current.mkdir(parents=True)
                    (current / "VERSION").write_text(installed + "\n", encoding="utf-8")
                    if protocol is not None:
                        (current / "UPGRADE-PROTOCOL.json").write_text(
                            json.dumps({"upgrade_protocol_version": protocol}), encoding="utf-8"
                        )
                    with patch.object(
                        tempfile, "mkdtemp",
                        side_effect=AssertionError("identity rejection must precede staging"),
                    ), self.assertRaisesRegex(upgrade_bridge_bootstrap.BridgeError, message):
                        upgrade_bridge_bootstrap.install(
                            target, artifacts["selection"], hosts_stopped=True
                        )
                    self.assertEqual((current / "VERSION").read_text("utf-8"), installed + "\n")

    def test_bridge_build_id_is_a_bounded_identifier_before_staging(self):
        invalid = (
            "../escape",
            r"..\escape",
            ".",
            "..",
            "/absolute",
            "C:drive",
            "unicode-\N{SNOWMAN}",
            "control\nvalue",
            "a" * 129,
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            feature = self._feature(root)
            artifacts = build_pack.build_protocol_bridge_artifacts(
                feature,
                version="1.15.0",
                build_prefix="build-id",
                bootstrap_source=SCRIPTS / "upgrade_bridge_bootstrap.py",
            )
            original = json.loads(artifacts["selection"].read_text(encoding="utf-8"))
            valid = dict(original, bridge_build_id="bridge_1.15-test")
            valid_path = artifacts["selection"].with_name("valid-selection.json")
            valid_path.write_text(json.dumps(valid), encoding="utf-8")
            self.assertEqual(
                upgrade_bridge_bootstrap._load_selection(valid_path)["bridge_build_id"],
                "bridge_1.15-test",
            )
            target = root / "target"
            current = target / ".wavefoundry/framework"
            current.mkdir(parents=True)
            (current / "VERSION").write_text("1.14.0\n", encoding="utf-8")
            for index, value in enumerate(invalid):
                with self.subTest(value=value):
                    selection = dict(original, bridge_build_id=value)
                    selection_path = artifacts["selection"].with_name(
                        f"invalid-selection-{index}.json"
                    )
                    selection_path.write_text(json.dumps(selection), encoding="utf-8")
                    with patch.object(
                        upgrade_bridge_bootstrap.tempfile,
                        "mkdtemp",
                        side_effect=AssertionError("invalid build id must precede staging"),
                    ), self.assertRaisesRegex(
                        upgrade_bridge_bootstrap.BridgeError,
                        "bridge_build_id must be a bounded ASCII identifier",
                    ):
                        upgrade_bridge_bootstrap.install(
                            target, selection_path, hosts_stopped=True
                        )
                    self.assertEqual(
                        (current / "VERSION").read_text(encoding="utf-8"),
                        "1.14.0\n",
                    )
                    self.assertFalse(any(
                        path.name.startswith("framework.rollback-")
                        for path in (target / ".wavefoundry").iterdir()
                    ))

    def test_windows_busy_lock_probe_preserves_existing_carrier_bytes(self):
        def refuse(_fd, _mode, _length):
            raise OSError("busy")

        fake_msvcrt = types.SimpleNamespace(
            LK_NBLCK=1,
            LK_UNLCK=2,
            locking=refuse,
        )
        with tempfile.TemporaryDirectory() as tmp:
            for offset in (0, upgrade_bridge_bootstrap.LIFECYCLE_OFFSET):
                with self.subTest(offset=offset):
                    carrier = Path(tmp) / f"lock-{offset}.bin"
                    before = b"active-owner-metadata\n"
                    carrier.write_bytes(before)
                    lock = upgrade_bridge_bootstrap._StrictLock(
                        carrier, offset, style="flock"
                    )
                    with patch.object(
                        upgrade_bridge_bootstrap.os, "name", "nt"
                    ), patch.dict(sys.modules, {"msvcrt": fake_msvcrt}):
                        with self.assertRaisesRegex(
                            upgrade_bridge_bootstrap.BridgeError,
                            "cannot acquire strict lock",
                        ):
                            lock.__enter__()
                    self.assertEqual(carrier.read_bytes(), before)

    def test_dashboard_lock_refusal_names_service_pid_and_stop_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            carrier = root / ".wavefoundry/locks/dashboard-server.lock"
            carrier.parent.mkdir(parents=True)
            carrier.write_text(json.dumps({"pid": 27688}), encoding="utf-8")
            hint = upgrade_bridge_bootstrap._lock_owner_hint(carrier)
            self.assertIn("Wavefoundry dashboard", hint)
            self.assertIn("pid 27688", hint)
            self.assertIn("wf_stop_dashboard()", hint)
            self.assertIn(str(root), hint)

    @unittest.skipIf(sys.platform == "win32", "POSIX lock styles use fcntl")
    def test_bridge_uses_product_lock_styles(self):
        import fcntl

        with tempfile.TemporaryDirectory() as tmp:
            record = upgrade_bridge_bootstrap._StrictLock(
                Path(tmp) / "record.lock", 17, style="record"
            )
            flock = upgrade_bridge_bootstrap._StrictLock(
                Path(tmp) / "flock.lock", 0, style="flock"
            )
            with patch.object(fcntl, "lockf", wraps=fcntl.lockf) as lockf_call, \
                 patch.object(fcntl, "flock", wraps=fcntl.flock) as flock_call:
                with record:
                    self.assertTrue(lockf_call.called)
                    self.assertFalse(flock_call.called)
                lockf_call.reset_mock()
                flock_call.reset_mock()
                with flock:
                    self.assertTrue(flock_call.called)
                    self.assertFalse(lockf_call.called)

    def test_bridge_lock_construction_matches_cross_platform_product_domains(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            feature = self._feature(root)
            artifacts = build_pack.build_protocol_bridge_artifacts(
                feature, version="1.15.0", build_prefix="lock-census",
                bootstrap_source=SCRIPTS / "upgrade_bridge_bootstrap.py",
            )
            target = root / "target"
            current = target / ".wavefoundry/framework"
            current.mkdir(parents=True)
            (current / "VERSION").write_text("1.14.0\n", encoding="utf-8")
            real_lock = upgrade_bridge_bootstrap._StrictLock
            observed = []

            def construct(path, offset, *, style):
                observed.append((Path(path).name, offset, style))
                return real_lock(path, offset, style=style)

            with patch.object(
                upgrade_bridge_bootstrap, "_StrictLock", side_effect=construct
            ):
                upgrade_bridge_bootstrap.install(
                    target, artifacts["selection"], hosts_stopped=True
                )
            self.assertEqual(
                observed,
                [
                    (
                        lifecycle_lock.LIFECYCLE_MUTATION_LOCK_REL.name,
                        lifecycle_lock.LIFECYCLE_MUTATION_LOCK_SENTINEL,
                        "record",
                    ),
                    (
                        review_evidence.PROJECT_STATE_PUBLICATION_LOCK_REL.name,
                        0,
                        "flock",
                    ),
                    (
                        dashboard_lib.DASHBOARD_SERVER_LOCK_NAME,
                        dashboard_lib._LOCK_BYTE_OFFSET,
                        "flock",
                    ),
                ],
            )

    def test_bridge_rejects_archive_swapped_at_lock_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            feature = self._feature(root)
            artifacts = build_pack.build_protocol_bridge_artifacts(
                feature, version="1.15.0", build_prefix="swap",
                bootstrap_source=SCRIPTS / "upgrade_bridge_bootstrap.py",
            )
            target = root / "target"
            current = target / ".wavefoundry/framework"
            current.mkdir(parents=True)
            (current / "VERSION").write_text("1.14.0\n", encoding="utf-8")
            original_enter = upgrade_bridge_bootstrap._StrictLock.__enter__
            swapped = False

            def enter(lock):
                nonlocal swapped
                value = original_enter(lock)
                if not swapped:
                    swapped = True
                    artifacts["bridge"].write_bytes(b"replacement")
                return value

            from unittest.mock import patch
            with patch.object(upgrade_bridge_bootstrap._StrictLock, "__enter__", enter):
                with self.assertRaisesRegex(upgrade_bridge_bootstrap.BridgeError, "hash mismatch"):
                    upgrade_bridge_bootstrap.install(
                        target, artifacts["selection"], hosts_stopped=True
                    )
            self.assertTrue((current / "VERSION").is_file())

    def test_full_install_ignores_preexisting_predictable_feature_stage_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            feature = self._feature(root)
            artifacts = build_pack.build_protocol_bridge_artifacts(
                feature,
                version="1.15.0",
                build_prefix="exclusive-stage",
                bootstrap_source=SCRIPTS / "upgrade_bridge_bootstrap.py",
            )
            target = root / "target"
            current = target / ".wavefoundry/framework"
            current.mkdir(parents=True)
            (current / "VERSION").write_text("1.14.0\n", encoding="utf-8")
            assets = target / ".wavefoundry/upgrade-assets"
            assets.mkdir()
            outside = root / "outside-sentinel.bin"
            before = b"outside-must-remain-unchanged"
            outside.write_bytes(before)
            predictable = assets / f".{feature.name}.tmp-{upgrade_bridge_bootstrap.os.getpid()}"
            try:
                predictable.symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")

            result = upgrade_bridge_bootstrap.install(
                target, artifacts["selection"], hosts_stopped=True
            )

            retained = Path(result["feature_archive"])
            self.assertEqual(outside.read_bytes(), before)
            self.assertFalse(retained.is_symlink())
            self.assertTrue(retained.is_file())
            self.assertEqual(retained.resolve().parent, assets.resolve())
            self.assertEqual(retained.read_bytes(), feature.read_bytes())

    def test_bridge_rejects_symlinked_wavefoundry_state_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            feature = self._feature(root)
            artifacts = build_pack.build_protocol_bridge_artifacts(
                feature, version="1.15.0", build_prefix="link",
                bootstrap_source=SCRIPTS / "upgrade_bridge_bootstrap.py",
            )
            target = root / "target"
            target.mkdir()
            outside = root / "outside"
            (outside / "framework").mkdir(parents=True)
            try:
                (target / ".wavefoundry").symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            with self.assertRaisesRegex(upgrade_bridge_bootstrap.BridgeError, "root_containment_failed"):
                upgrade_bridge_bootstrap.install(
                    target, artifacts["selection"], hosts_stopped=True
                )
            self.assertTrue((outside / "framework").is_dir())


if __name__ == "__main__":
    unittest.main()
