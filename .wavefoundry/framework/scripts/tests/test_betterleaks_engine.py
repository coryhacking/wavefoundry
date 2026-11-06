"""Offline scanner worker controls; engine qualification shares this module."""
from __future__ import annotations

import json
import gzip
import tomllib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from unittest import mock

sys.dont_write_bytecode = True
SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from wave_lint_lib import betterleaks_worker as worker


class OfflineWorkerTests(unittest.TestCase):
    def tearDown(self):
        worker.close_worker()

    def _fake(self, code):
        client = worker._Client([sys.executable, "-B", "-c", code])
        self.addCleanup(client.close)
        return client

    def _assert_error(self, expected, call):
        with self.assertRaises(worker.WorkerError) as raised:
            call()
        self.assertEqual(raised.exception.code, expected)
        self.assertEqual(str(raised.exception), expected)

    def test_actual_parser_reuses_child_and_close_reaps_it(self):
        self.assertEqual(worker.worker_request("parse_toml", {"text": 'title = "fixture"'}),
                         {"title": "fixture"})
        process = worker._CLIENT._process
        self.assertIsNone(process.poll())
        self.assertEqual(worker.worker_request("parse_toml", {"text": "n = 2"}), {"n": 2})
        self.assertIs(worker._CLIENT._process, process)
        worker.close_worker()
        self.assertIsNotNone(process.poll())
        self.assertIsNone(worker._CLIENT)

    def test_module_eviction_reaps_child_and_retired_function_cannot_restart(self):
        import gc
        import importlib.util
        import weakref
        name = "wave_lint_lib._lifetime_probe"
        spec = importlib.util.spec_from_file_location(name, worker.__file__)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        self.addCleanup(sys.modules.pop, name, None)
        spec.loader.exec_module(module)
        request, close = module.worker_request, module.close_worker
        self.addCleanup(close)
        self.assertEqual(request("parse_toml", {"text": "n=1"}), {"n": 1})
        process = module._CLIENT._process
        self.assertIsNone(process.poll())
        reference = weakref.ref(module)
        del sys.modules[name]
        del module
        gc.collect()
        self.assertIsNone(reference())
        self.assertIsNotNone(process.poll())
        with self.assertRaisesRegex(RuntimeError, "worker_closed"):
            request("parse_toml", {"text": "n=2"})

    def test_actual_path_exclusion_is_a_bounded_worker_operation(self):
        payload = {"cache_key": "path-control", "config": {
            "rules": [{"id": "fixture", "regex": "SYNTHETIC"}],
            "allowlist": {"paths": [r"^docs/"]}}}
        self.assertEqual(worker.worker_request("path_excluded", {**payload, "path": "docs/readme.md"}),
                         {"excluded": True})
        self.assertEqual(worker.worker_request("path_excluded", {**payload, "path": "src/app.py"}),
                         {"excluded": False})
        self._assert_error("worker_input_too_large", lambda: worker.worker_request(
            "path_excluded", {**payload, "path": "a" * 8193}))

    def test_invalid_toml_never_returns_input_or_exception_text(self):
        self._assert_error("invalid_configuration", lambda: worker.worker_request(
            "parse_toml", {"text": 'fixture_sensitive_canary = "unterminated'}))

    def test_actual_parser_config_size_limit(self):
        self._assert_error("worker_input_too_large", lambda: worker.worker_request(
            "parse_toml", {"text": "#" * (2 * 1024 * 1024 + 1)}))

    def test_parent_wire_limit_refuses_before_starting_a_child(self):
        client = worker._Client()
        self.addCleanup(client.close)
        with mock.patch.object(worker, "MAX_REQUEST_BYTES", 128):
            self._assert_error("worker_input_too_large", lambda: client.request(
                "parse_toml", {"text": "#" * 256}))
        self.assertIsNone(client._process)

    def test_node_and_depth_limits_do_not_expand_unbounded_containers(self):
        self._assert_error("worker_input_too_large", lambda: worker._encode(
            [0] * 250_001, worker.MAX_REQUEST_BYTES))
        nested = []
        for _ in range(66):
            nested = [nested]
        self._assert_error("worker_input_too_large", lambda: worker._encode(
            nested, worker.MAX_REQUEST_BYTES))

    def test_unknown_operation_is_not_a_program_execution_surface(self):
        client = worker._Client()
        self.addCleanup(client.close)
        self._assert_error("invalid_operation", lambda: client.request("eval", {"text": "1+1"}))
        self.assertIsNone(client._process)

    def test_hung_child_is_killed_and_does_not_trigger_serial_fallback(self):
        client = self._fake("import sys,time; sys.stdin.buffer.readline(); time.sleep(3600)")
        observed = []
        dispose = worker._dispose
        def capture(process):
            if process is not None:
                observed.append(process)
            dispose(process)
        start = time.monotonic()
        with mock.patch.object(worker, "_dispose", side_effect=capture):
            self._assert_error("worker_timeout", lambda: client.request(
                "parse_toml", {"text": "n=1"}, timeout=0.15))
        self.assertLess(time.monotonic() - start, 3)
        self.assertTrue(observed)
        self.assertTrue(all(p.poll() is not None for p in observed))
        self.assertIsNone(client._process)

    def test_crashed_child_is_not_a_clean_empty_result(self):
        client = self._fake("import sys,os; sys.stdin.buffer.readline(); os._exit(7)")
        self._assert_error("worker_crashed", lambda: client.request("parse_toml", {"text": "n=1"}))
        self.assertIsNone(client._process)

    def test_timeout_during_startup_disposes_the_late_child(self):
        import subprocess_util
        original = subprocess_util.isolated_popen
        started = []
        def delayed(*args, **kwargs):
            time.sleep(0.1)
            process = original(*args, **kwargs)
            started.append(process)
            return process
        client = worker._Client()
        self.addCleanup(client.close)
        with mock.patch.object(subprocess_util, "isolated_popen", side_effect=delayed):
            self._assert_error("worker_timeout", lambda: client.request(
                "parse_toml", {"text": "n=1"}, timeout=0.03))
        self.assertEqual(len(started), 1)
        self.assertIsNotNone(started[0].poll())
        self.assertIsNone(client._process)

    def test_close_during_request_cancels_and_reaps_owned_child(self):
        import threading
        client = self._fake("import sys,time; sys.stdin.buffer.readline(); time.sleep(3600)")
        outcome = []
        def call():
            try:
                client.request("parse_toml", {"text": "n=1"}, timeout=3)
            except worker.WorkerError as exc:
                outcome.append(exc.code)
        thread = threading.Thread(target=call)
        thread.start()
        deadline = time.monotonic() + 2
        while client._process is None and time.monotonic() < deadline:
            time.sleep(0.005)
        process = client._process
        self.assertIsNotNone(process)
        client.close()
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive())
        self.assertIsNotNone(process.poll())
        self.assertEqual(len(outcome), 1)

    def test_malformed_or_wrong_revision_response_is_refused(self):
        for response in ["not-json", '{"id":999,"ok":true,"result":{}}',
                         '{"id":1,"ok":true,"result":[]}',
                         '{"id":1,"ok":true,"result":{},"extra":1}',
                         '{"id":1,"id":1,"ok":true,"result":{}}',
                         '{"id":1,"ok":false,"error":"fixture_sensitive_canary"}']:
            with self.subTest(response=response):
                client = self._fake("import sys; sys.stdin.buffer.readline(); print(" + repr(response) + ",flush=True)")
                self._assert_error("worker_protocol", lambda: client.request("parse_toml", {"text": "n=1"}))
                self.assertIsNone(client._process)

    def test_response_wire_limit_kills_child_before_parsing_large_output(self):
        client = self._fake("import sys; sys.stdin.buffer.readline(); print('x'*512,flush=True)")
        with mock.patch.object(worker, "MAX_RESPONSE_BYTES", 128):
            self._assert_error("worker_response_too_large", lambda: client.request("parse_toml", {"text": "n=1"}))
        self.assertIsNone(client._process)

    def test_child_exits_when_the_owner_closes_input(self):
        import subprocess_util
        process = subprocess_util.isolated_popen(
            [sys.executable, "-B", worker.__file__, "--worker"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        self.addCleanup(worker._dispose, process)
        process.stdin.close()
        self.assertEqual(process.wait(timeout=3), 0)
        self.assertEqual(process.stdout.read(), b"")
        self.assertEqual(process.stderr.read(), b"")

    def test_actual_child_denies_network_and_subprocess_actions(self):
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "scripts" / "wave_lint_lib"
            package.mkdir(parents=True)
            shutil.copyfile(worker.__file__, package / "betterleaks_worker.py")
            shutil.copyfile(SCRIPTS / "bytecode_cache.py", package.parent / "bytecode_cache.py")
            (package / "__init__.py").write_text("")
            (package / "betterleaks_engine.py").write_text(textwrap.dedent('''\
                import socket, subprocess, sys
                class BetterleaksEngine:
                    def __init__(self, config):
                        self.blocked = []
                        try:
                            sock = socket.socket()
                            sock.close()
                        except PermissionError:
                            self.blocked.append("network")
                        try:
                            subprocess.run([sys.executable, "-c", "pass"], check=True)
                        except PermissionError:
                            self.blocked.append("process")
                    def scan(self, content, path, metadata_only=False):
                        return {"findings": [], "complete": True,
                                "diagnostics": [], "blocked": self.blocked}
                '''))
            client = worker._Client([sys.executable, "-B", str(package / "betterleaks_worker.py"), "--worker"])
            self.addCleanup(client.close)
            result = client.request("scan", {"config": {"rules": []}, "content": "", "path": "fixture.txt"})
            self.assertEqual(result["blocked"], ["network", "process"])
            self.assertTrue(result["complete"])
            client.close()

    def test_execution_key_change_restarts_child_and_loads_changed_engine(self):
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "scripts" / "wave_lint_lib"
            package.mkdir(parents=True)
            shutil.copyfile(worker.__file__, package / "betterleaks_worker.py")
            shutil.copyfile(SCRIPTS / "bytecode_cache.py", package.parent / "bytecode_cache.py")
            (package / "__init__.py").write_text("")
            engine_path = package / "betterleaks_engine.py"
            template = textwrap.dedent('''\
                class BetterleaksEngine:
                    def __init__(self, config):
                        pass
                    def scan(self, content, path, metadata_only=False):
                        return {"findings": [], "complete": True,
                                "diagnostics": [], "version": VERSION}
                ''')
            engine_path.write_text(template.replace("VERSION", "1"))
            client = worker._Client([sys.executable, "-B", str(package / "betterleaks_worker.py"), "--worker"])
            self.addCleanup(client.close)
            payload = {"config": {"rules": []}, "cache_key": "version-1",
                       "content": "", "path": "fixture.txt"}
            self.assertEqual(client.request("scan", payload)["version"], 1)
            old_process = client._process
            engine_path.write_text(template.replace("VERSION", "2"))
            self.assertEqual(client.request("parse_toml", {"text": "n=1"}), {"n": 1})
            self.assertIs(client._process, old_process)
            # Unchanged identity deliberately keeps the existing imported code.
            self.assertEqual(client.request("scan", payload)["version"], 1)
            payload["cache_key"] = "version-2"
            client.request("configure", {"config": {"rules": []}, "cache_key": "version-2"})
            self.assertEqual(client.request("scan", payload)["version"], 2)
            self.assertIsNotNone(old_process.poll())
            self.assertIsNot(client._process, old_process)
            second_process = client._process
            engine_path.write_text(template.replace("VERSION", "3"))
            payload["cache_key"] = "version-3"
            self.assertEqual(client.request("scan", payload)["version"], 3)
            self.assertIsNotNone(second_process.poll())
            self.assertIsNot(client._process, second_process)
            client.close()



class OfflineEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from wave_lint_lib.betterleaks_engine import BetterleaksEngine
        cls.Engine = BetterleaksEngine
        cls.fixtures = SCRIPTS / "tests/fixtures/betterleaks"
        cls.config = tomllib.loads((cls.fixtures / "upstream.toml").read_text())
        cls.engine = BetterleaksEngine(cls.config)

    @staticmethod
    def normalized(finding):
        match = finding.get("match", {})
        return (finding["rule_id"], finding.get("confidence", ""),
                match.get("value", ""), match.get("full", ""),
                tuple(sorted(match.get("captures", {}).items())),
                tuple(finding.get("location", {}).get(k, 0) for k in
                      ("start_line", "end_line", "start_column", "end_column")),
                tuple(sorted(tuple(sorted((OfflineEngineTests.normalized(c), c.get("optional", False))
                                          for c in group["components"]))
                             for group in finding.get("component_sets", []))))

    def test_all_474_rules_against_pinned_full_configuration_oracle(self):
        reported, components, cases, negatives = set(), set(), 0, 0
        with gzip.open(self.fixtures / "oracle.jsonl.gz", "rt") as stream:
            for line in stream:
                row = json.loads(line)
                result = self.engine.scan(row["content"], row["path"])
                with self.subTest(case=row["case_id"], rule=row["rule_id"]):
                    self.assertTrue(result["complete"], result["diagnostics"])
                    self.assertEqual(sorted(map(self.normalized, result["findings"])),
                                     sorted(map(self.normalized, row["findings"])))
                for finding in result["findings"]:
                    reported.add(finding["rule_id"])
                    components.update(c["rule_id"] for group in finding.get("component_sets", []) for c in group["components"])
                cases += 1
                negatives += row["label"] == "negative"
        self.assertEqual(cases, 1511)
        self.assertEqual(negatives, 916)
        self.assertEqual(len(reported | components), 473)
        unreachable = {r["id"] for r in self.config["rules"]} - reported - components
        self.assertEqual(unreachable, {"polymarket-address"})
        orphan = next(r for r in self.config["rules"] if r["id"] == "polymarket-address")
        self.assertTrue(orphan["skipReport"])
        self.assertFalse(any(c["id"] == orphan["id"] for r in self.config["rules"] for c in r.get("components", [])))
        # An explicitly isolated probe proves the detector, not default reporting.
        row = json.loads((self.fixtures / "orphan-isolated-oracle.jsonl").read_text().splitlines()[0])
        isolated = self.Engine({"rules": [{**orphan, "skipReport": False}]})
        self.assertEqual([f["rule_id"] for f in isolated.scan(row["content"], row["path"])["findings"]], [orphan["id"]])

    def test_equal_specificity_keeps_both_but_stronger_owner_wins(self):
        rules = [{"id": name, "regex": "TOKEN"} for name in ("first", "second")]
        self.assertEqual(len(self.Engine({"rules": rules}).scan("TOKEN", "file")["findings"]), 2)
        rules[1]["specificity"] = 1
        self.assertEqual([f["rule_id"] for f in self.Engine({"rules": rules}).scan("TOKEN", "file")["findings"]], ["second"])

    def test_independent_near_misses_cover_rules_without_upstream_negatives(self):
        negatives, baselines, count = set(), set(), 0
        orphan = next(r for r in self.config["rules"] if r["id"] == "polymarket-address")
        isolated = self.Engine({**self.config, "rules": [{**orphan, "skipReport": False}]})
        with gzip.open(self.fixtures / "independent-negative-oracle.jsonl.gz", "rt") as stream:
            for line in stream:
                row = json.loads(line)
                result = (isolated if row["isolated"] else self.engine).scan(row["content"], row["path"])
                with self.subTest(case=row["case_id"]):
                    self.assertTrue(result["complete"], result["diagnostics"])
                    self.assertEqual(sorted(map(self.normalized, result["findings"])),
                                     sorted(map(self.normalized, row["findings"])))
                ids = {f["rule_id"] for f in result["findings"]}
                ids.update(c["rule_id"] for f in result["findings"] for group in f.get("component_sets", []) for c in group["components"])
                if row["rule_id"] not in ids:
                    negatives.add(row["rule_id"])
                else:
                    baselines.add(row["rule_id"])
                count += 1
        self.assertEqual(count, 1521)
        self.assertEqual(len(negatives), 169)
        self.assertEqual(len(baselines), 169)

    def test_profile_inspection_compiles_without_executing_imported_programs(self):
        from wave_lint_lib.secrets_validators import inspect_ruleset_compatibility
        self.addCleanup(worker.close_worker)
        config = {**self.config, "wavefoundryProfile": "betterleaks-v2-8f376ff9",
                  "allowlist": {"description": "fixture", "paths": [r"^ignored/"], "regexes": [r"^NULL$"], "stopwords": []}}
        result = inspect_ruleset_compatibility(config)
        self.assertEqual(result["status"], "within_checked_subset", result)
        self.assertEqual(result["rules_checked"], 474)
        result = inspect_ruleset_compatibility({**config, "futureDetector": True})
        self.assertEqual(result["status"], "unsupported")
        with mock.patch.object(worker, "worker_request", side_effect=worker.WorkerError("worker_timeout")):
            self.assertEqual(inspect_ruleset_compatibility(config)["status"], "incomplete")

    def test_shipped_profile_preserves_local_policy_and_declared_filter_correction(self):
        shipped = tomllib.loads((SCRIPTS.parent / "scan-rules.toml").read_text())
        baseline = tomllib.loads((self.fixtures / "baseline.toml").read_text())
        self.assertEqual(shipped["wavefoundryProfile"], "betterleaks-v2-8f376ff9")
        self.assertEqual(shipped["rules"], self.config["rules"])
        self.assertEqual(shipped["policy"], baseline["policy"])
        for key in ("paths", "regexes", "stopwords"):
            self.assertEqual(shipped["allowlist"][key], baseline["allowlist"][key])
        self.assertEqual(shipped["filter"], self.config["filter"].replace(
            "(?i)^true|false|null$", "(?i)^(?:true|false|null)$"))
        engine = self.Engine({"filter": shipped["filter"],
                              "rules": [{"id": "fixture", "regex": "false|XfalseY"}]})
        self.assertEqual(engine.scan("false", "f")["findings"], [])
        self.assertEqual(engine.scan("XfalseY", "f")["findings"][0]["match"]["value"], "XfalseY")

    def test_upstream_loader_rejects_unknown_inherited_fields_and_invalid_allowlist(self):
        from wave_lint_lib.secrets_validators import load_merged_ruleset
        self.addCleanup(worker.close_worker)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            framework = root / ".wavefoundry/framework/scan-rules.toml"
            framework.parent.mkdir(parents=True)
            framework.write_text('wavefoundryProfile = "betterleaks-v2-8f376ff9"\n[[rules]]\nid="r"\nregex="TOKEN"\n')
            project = root / "docs/scan-rules.toml"
            project.parent.mkdir()
            project.write_text('futureDetector = true\n')
            self.assertTrue(load_merged_ruleset(root)[2])
            project.write_text('[allowlist]\npaths = "invalid"\n')
            self.assertTrue(load_merged_ruleset(root)[2])
            project.write_text('[allowlist]\npaths = ["^ignored/"]\n')
            rules, policy, errors = load_merged_ruleset(root)
            self.assertFalse(errors)
            self.assertEqual(policy["_betterleaks_config"]["allowlist"]["paths"], ["^ignored/"])

    def test_capture_selection_and_empty_explicit_group(self):
        rules = [{"id": "capture", "regex": "(?P<one>a)?(?P<two>b)", "valueGroup": 1}]
        hit = self.Engine({"rules": rules}).scan("b", "file")["findings"][0]
        self.assertEqual(hit["match"]["value"], "")
        self.assertEqual(hit["match"]["captures"], {"two": "b"})
        rules[0]["valueGroup"] = 0
        self.assertEqual(self.Engine({"rules": rules}).scan("b", "file")["findings"][0]["match"]["value"], "b")

    def test_required_optional_and_directional_component_boundaries(self):
        rules = [{"id": "primary", "regex": "PRIMARY", "components": [{"id": "part", "within": "+2L"}]},
                 {"id": "part", "regex": "PART", "skipReport": True}]
        engine = self.Engine({"rules": rules})
        self.assertTrue(engine.scan("PRIMARY\nPART", "f")["findings"])
        self.assertFalse(engine.scan("PRIMARY\nother\nPART", "f")["findings"])
        self.assertFalse(engine.scan("PART\nPRIMARY", "f")["findings"])
        rules[0]["components"][0]["optional"] = True
        self.assertTrue(self.Engine({"rules": rules}).scan("PRIMARY", "f")["findings"])
        rules[1]["regex"] = "PART(?P<value>[0-9])"
        self.assertEqual(len(self.Engine({"rules": rules}).scan("PRIMARY\nPART1 PART2", "f")["findings"][0]["component_sets"]), 2)

    def test_runtime_filter_failure_retains_hit_and_marks_incomplete(self):
        engine = self.Engine({"rules": [{"id": "r", "regex": "TOKEN", "filter": 'fromBase64("bad*") == ""'}]})
        result = engine.scan("TOKEN", "f")
        self.assertFalse(result["complete"])
        self.assertEqual(len(result["findings"]), 1)
        self.assertEqual(result["diagnostics"], ["filter_evaluation_error:r"])

    def test_unsupported_construct_and_missing_component_refuse_configuration(self):
        from wave_lint_lib.betterleaks_engine import ConfigurationError
        from wave_lint_lib.expr_filter import CompileError
        with self.assertRaises(CompileError):
            self.Engine({"rules": [{"id": "r", "regex": "TOKEN", "filter": "http.get(finding.secret)"}]})
        with self.assertRaises(ConfigurationError):
            self.Engine({"rules": [{"id": "r", "regex": "TOKEN", "components": [{"id": "absent"}]}]})
        with self.assertRaises(ConfigurationError):
            self.Engine({"rules": [{"id": "r", "regex": "TOKEN", "futureDetector": True}]})

    def test_match_and_component_caps_are_explicit_incompleteness(self):
        from wave_lint_lib import betterleaks_engine as module
        engine = self.Engine({"rules": [{"id": "r", "regex": "TOKEN"}]})
        with mock.patch.object(module, "MAX_MATCHES", 1):
            result = engine.scan("TOKEN TOKEN", "f")
        self.assertFalse(result["complete"])
        self.assertIn("match_limit", result["diagnostics"])
        rules = [{"id": "r", "regex": "ROOT", "components": [{"id": "a"}, {"id": "b"}]},
                 {"id": "a", "regex": "A[0-9]", "skipReport": True},
                 {"id": "b", "regex": "B[0-9]", "skipReport": True}]
        engine = self.Engine({"rules": rules})
        with mock.patch.object(module, "MAX_COMPONENT_SETS", 2):
            result = engine.scan("ROOT A1 A2 B1 B2", "f")
        self.assertFalse(result["complete"])
        self.assertEqual(len(result["findings"][0]["component_sets"]), 2)
        self.assertIn("component_set_limit", result["diagnostics"])

    def test_real_worker_scan_and_inactive_provider_programs(self):
        self.addCleanup(worker.close_worker)
        config = {"rules": [{"id": "r", "regex": "TOKEN", "validate": 'http.get("https://invalid.example/")',
                              "analyze": "os.exec(finding.secret)", "revoke": "unknown.action()"}]}
        with mock.patch.dict("os.environ", {"BETTERLEAKS_VALIDATE": "true", "BETTERLEAKS_ANALYZE": "true"}):
            result = worker.worker_request("scan", {"config": config, "content": "TOKEN", "path": "f", "cache_key": "inert-actions"})
        self.assertTrue(result["complete"])
        self.assertEqual([f["rule_id"] for f in result["findings"]], ["r"])

    def test_package_collector_includes_runtime_assets_and_excludes_oracles(self):
        import build_pack
        framework = SCRIPTS.parent
        paths = {p.relative_to(framework).as_posix() for p, _ in build_pack.collect_files(framework)}
        for name in ("cl100k_base.tiktoken.gz", "words.txt.gz", "manifest.json", "NOTICE.md"):
            self.assertIn("scan/" + name, paths)
        self.assertFalse(any(p.startswith("scripts/tests/") for p in paths))


if __name__ == "__main__":
    unittest.main()
