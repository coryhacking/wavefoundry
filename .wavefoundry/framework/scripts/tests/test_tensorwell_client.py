"""Isolated optional-service contracts; never access an installed service."""
from __future__ import annotations

import contextlib
import copy
import hashlib
import importlib
import io
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))
import tensorwell_client as tc

INSTANCE = "a" * 64
TOKEN = "b" * 64


def descriptor(task):
    return {"id": "arctic-fp16-coreml" if task == "embedding" else "minilm-fp16-coreml",
            "identity": ("sha256:5670c9e9f64e33744416fa5851a26656f42dd24e99e7dde0b106d00617b1c1c7" if task == "embedding"
                         else "sha256:3a14f1775368230d55eecc1fec7a144b17b845e5706bc47757cb45470df699f8"),
            "task": task, "precision": "fp16", "dimensions": 384 if task == "embedding" else None,
            "requested_provider": "CoreMLExecutionProvider", "registered_provider": "CoreMLExecutionProvider"}


@unittest.skipIf(os.name == "nt", "Private POSIX discovery fixtures; native Windows service use remains unsupported")
class ClientTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.state = self.home / ".tensorwell"
        self.state.mkdir(mode=0o700)
        self.enterContext(patch.object(tc.Path, "home", return_value=self.home))
        self.enterContext(patch.object(tc.platform, "system", return_value="Darwin"))
        self.enterContext(patch.object(tc.platform, "machine", return_value="arm64"))
        self.enterContext(patch.dict(os.environ, {"WAVEFOUNDRY_DISABLE_TENSORWELL": "0",
                "WAVEFOUNDRY_EMBED_PROVIDER": "auto", "WAVEFOUNDRY_EMBED_PROVIDER_SELECTED": "",
                "WAVEFOUNDRY_DISABLE_RERANKER": "0"}))
        for key, value in (("_pair", None), ("_cache_until", 0), ("_backoff_until", 0), ("_startup_scheduled", False), ("_startup_worker", None)):
            self.enterContext(patch.object(tc, key, value))
        self.enterContext(patch.object(tc, "_status", {"backend": "local", "reason": "not_checked", "startup": "not_scheduled", "profiles": []}))
        self.enterContext(patch.object(tc, "_roles", {role: {"selection": None, "last_attempt": None, "last_success": None}
                                                    for role in tc._ROLES}))
        self.enterContext(patch.object(tc, "_owners", {slot: {"ref": None, "complete": True, "model": None}
                                                     for slot in tc._OWNER_SLOTS}))
        self.enterContext(patch.object(tc, "_availability", {"state": "not_checked", "reason": "not_checked",
                                                           "observed_at": None, "observed_monotonic": None}))
        self.enterContext(patch.object(tc, "_process_pid", os.getpid()))
        self.enterContext(patch.object(tc, "_sequence", 0))
        self.models = [descriptor("embedding"), descriptor("reranking")]
        self.requests = []
        self.reply = None
        self.server = None

    def endpoint(self, port=12345, **extra):
        data = {"url": f"http://127.0.0.1:{port}", "pid": 4321, "instance_id": INSTANCE, "api_version": "v1", **extra}
        self.write("endpoint.json", json.dumps(data).encode())
        self.write("token", TOKEN.encode())
        return tc._Snapshot(port, INSTANCE, TOKEN)

    def write(self, name, value):
        path = self.state / name
        path.write_bytes(value)
        path.chmod(0o600)

    def answer(self, snapshot, path, deadline, body=None):
        value = json.loads(body) if body is not None else None
        self.requests.append((path, value))
        if self.reply is not None:
            result = self.reply(path, value)
            if result is not None:
                return result
        if path == "/health/ready":
            return {"instance_id": INSTANCE, "status": "ready"}
        if path == "/v1/models":
            return {"instance_id": INSTANCE, "data": self.models}
        embedding = path == "/v1/embeddings"
        items = value["input" if embedding else "documents"]
        return {"instance_id": INSTANCE, "model": descriptor("embedding" if embedding else "reranking"),
                "data": [{"index": i, "embedding": [1.0] + [0.0] * 383} if embedding
                         else {"index": i, "score": float(i) - 2.5} for i, text in enumerate(items)]}

    def fake_ready(self):
        snapshot = self.endpoint()
        self.enterContext(patch.object(tc, "_http", side_effect=self.answer))
        return snapshot

    def serve(self, custom=None):
        owner = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_GET(self):
                self.respond()
            def do_POST(self):
                self.respond()
            def respond(self):
                size = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(size) if size else None
                owner.assertEqual(self.headers["Authorization"], "Bearer " + TOKEN)
                owner.assertEqual(self.headers["Host"], f"127.0.0.1:{owner.server.server_port}")
                if custom:
                    custom(self)
                    return
                value = owner.answer(None, self.path, time.monotonic() + 1, body)
                encoded = json.dumps(value).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                try:
                    self.wfile.write(encoded)
                except OSError:
                    pass  # rejection/timeout deliberately closes the client
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        worker.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        return self.endpoint(self.server.server_port)

    def test_qualified_pair_roles_order_empty_unicode(self):
        self.fake_ready()
        embedder = tc.select_embedder(tc.EMBEDDING_MODEL)
        reranker = tc.select_reranker(tc.RERANKER_MODEL)
        self.assertIsNotNone(embedder)
        self.assertEqual(len(list(embedder.embed(["", "café 🌊"]))), 2)
        self.assertEqual(embedder.embed_query("Represent this sentence for searching relevant passages: literal")[0], 1)
        self.assertEqual(reranker.rerank("raw query", ["a", "b"]), [-2.5, -1.5])
        self.assertEqual(list(embedder.embed([])), [])
        self.assertEqual(reranker.rerank("", []), [])
        requests = [body for path, body in self.requests if path == "/v1/embeddings"]
        self.assertEqual(requests[0]["input"], ["", "café 🌊"])
        self.assertEqual(requests[0]["role"], "document")
        self.assertEqual(requests[1]["role"], "query")
        self.assertEqual(requests[1]["input"], ["Represent this sentence for searching relevant passages: literal"])
        self.assertEqual(tc.status_snapshot()["backend"], "tensorwell")

    def test_pair_rejects_partial_identity_dimensions_provider_precision(self):
        self.fake_ready()
        original = copy.deepcopy(self.models)
        mutants = [[original[0]], [original[1]]]
        for field, value in (("identity", "sha256:" + "0" * 64), ("dimensions", 385), ("precision", "int8"),
                             ("registered_provider", "CPUExecutionProvider"), ("task", "reranking")):
            rows = copy.deepcopy(original)
            rows[0][field] = value
            mutants.append(rows)
        mutants.append(original + [original[0]])
        mutants.append(original + [original[1]])
        for models in mutants:
            with self.subTest(models=models):
                self.models = models
                tc._pair, tc._cache_until, tc._backoff_until = None, 0, 0
                self.assertIsNone(tc.select_embedder(tc.EMBEDDING_MODEL))
                self.assertEqual(tc.status_snapshot()["reason"], "incompatible_profiles")
        self.models = original
        tc._pair, tc._cache_until, tc._backoff_until = None, 0, 0
        self.assertIsNone(tc.select_embedder(tc.EMBEDDING_MODEL, "int8"))
        self.assertIsNone(tc.select_embedder("other"))

    def test_policy_controls_no_discovery(self):
        cases = [{"WAVEFOUNDRY_DISABLE_TENSORWELL": "1"}, {"WAVEFOUNDRY_EMBED_PROVIDER": "cpu"},
                 {"WAVEFOUNDRY_EMBED_PROVIDER": "cuda"}, {"WAVEFOUNDRY_EMBED_PROVIDER_SELECTED": "CPUExecutionProvider"}]
        for env in cases:
            with patch.dict(os.environ, env), patch.object(tc, "_discovery") as discovery:
                self.assertIsNone(tc.select_embedder(tc.EMBEDDING_MODEL))
                discovery.assert_not_called()
        with patch.object(tc.platform, "system", return_value="Windows"), patch.object(tc, "_discovery") as discovery:
            self.assertIsNone(tc.select_embedder(tc.EMBEDDING_MODEL))
            discovery.assert_not_called()
        with patch.dict(os.environ, {"WAVEFOUNDRY_DISABLE_RERANKER": "yes"}), patch.object(tc, "_qualified_pair") as pair:
            self.assertIsNone(tc.select_reranker(tc.RERANKER_MODEL))
            pair.assert_not_called()

    def test_discovery_safe_files_bounds_and_endpoint_schema(self):
        self.endpoint()
        self.assertEqual(tc._discovery(time.monotonic() + 1), tc._Snapshot(12345, INSTANCE, TOKEN))
        endpoints = [{"url": "http://localhost:12345"}, {"url": "http://127.0.0.1:12345/"},
                     {"url": "http://127.0.0.1:65536"}, {"url": "https://127.0.0.1:12345"},
                     {"url": "http://127.0.0.1:12345?token=x"}, {"instance_id": "a" * 32},
                     {"api_version": "v2"}, {"pid": True}, {"unknown": 1}]
        for extra in endpoints:
            self.endpoint(**extra)
            with self.assertRaises((ValueError, TypeError)):
                tc._discovery(time.monotonic() + 1)
        self.endpoint()
        (self.state / "token").chmod(0o644)
        with self.assertRaises(ValueError): tc._discovery(time.monotonic() + 1)
        self.endpoint()
        token = self.state / "token"
        token.unlink()
        token.symlink_to(self.home / "missing")
        with self.assertRaises(OSError): tc._discovery(time.monotonic() + 1)
        token.unlink()
        self.endpoint()
        self.state.chmod(0o755)
        with self.assertRaises(ValueError): tc._discovery(time.monotonic() + 1)
        self.state.chmod(0o700)
        self.write("endpoint.json", b" " * 4097)
        with self.assertRaises(ValueError): tc._discovery(time.monotonic() + 1)

    def test_private_files_owner_regular_and_directory_link(self):
        self.endpoint()
        with patch.object(tc.os, "getuid", return_value=os.getuid() + 1):
            with self.assertRaises(ValueError): tc._discovery(time.monotonic() + 1)
        token = self.state / "token"
        token.unlink()
        os.mkfifo(token, mode=0o600)
        with self.assertRaises(ValueError): tc._discovery(time.monotonic() + 1)
        directory = os.open(self.state, os.O_RDONLY | os.O_DIRECTORY)
        try:
            with self.assertRaises(ValueError): tc._private_file(directory, "token", 64)
        finally:
            os.close(directory)
        token.unlink()
        self.endpoint()
        original_stat = tc.os.fstat
        def wrong_file_owner(fd):
            info = original_stat(fd)
            if stat_is_regular(info):
                return SimpleNamespace(st_uid=os.getuid() + 1, st_mode=info.st_mode, st_size=info.st_size)
            return info
        def stat_is_regular(info):
            import stat
            return stat.S_ISREG(info.st_mode)
        with patch.object(tc.os, "fstat", side_effect=wrong_file_owner):
            with self.assertRaises(ValueError): tc._discovery(time.monotonic() + 1)
        real = self.home / "private"
        self.state.rename(real)
        self.state.symlink_to(real, target_is_directory=True)
        with self.assertRaises(OSError): tc._discovery(time.monotonic() + 1)

    def test_endpoint_token_endpoint_rotation(self):
        snapshot = self.endpoint()
        read = tc._private_file
        observations = []
        def rotated(directory, name, limit):
            observations.append(name)
            data = read(directory, name, limit)
            if len(observations) == 1:
                data += b" "
            return data
        with patch.object(tc, "_private_file", side_effect=rotated):
            self.assertEqual(tc._discovery(time.monotonic() + 1), snapshot)
        self.assertEqual(observations, ["endpoint.json", "token", "endpoint.json"] * 2)

    def test_transport_no_proxy_redirect_and_response_cap(self):
        snapshot = self.serve()
        with patch.dict(os.environ, {"HTTP_PROXY": "http://127.0.0.1:1", "http_proxy": "http://127.0.0.1:1"}):
            self.assertEqual(tc._http(snapshot, "/health/ready", time.monotonic() + 1)["status"], "ready")
        self.server.shutdown()
        def redirect(handler):
            handler.send_response(302)
            handler.send_header("Location", "http://127.0.0.1:1")
            handler.end_headers()
        snapshot = self.serve(redirect)
        with self.assertRaises(ValueError): tc._http(snapshot, "/health/ready", time.monotonic() + 1)
        self.server.shutdown()
        def huge(handler):
            handler.send_response(200)
            handler.send_header("Content-Type", "application/json")
            handler.send_header("Content-Length", str(tc.MAX_RESPONSE_BYTES + 1))
            handler.end_headers()
            handler.wfile.write(json.dumps({"instance_id": INSTANCE, "status": "ready"}).encode())
        snapshot = self.serve(huge)
        with self.assertRaises(ValueError): tc._http(snapshot, "/health/ready", time.monotonic() + 1)

    def test_response_instance_json_and_body_limits(self):
        snapshot = self.serve()
        self.reply = lambda path, body: {"instance_id": "c" * 64, "status": "ready"}
        with self.assertRaises(ValueError): tc._http(snapshot, "/health/ready", time.monotonic() + 1)
        self.reply = lambda path, body: {"instance_id": INSTANCE, "padding": "x" * ((2 << 20) + 1)}
        with self.assertRaises(ValueError): tc._http(snapshot, "/health/ready", time.monotonic() + 1)
        with self.assertRaises(ValueError): tc._json(b'{"same":1,"same":2}')
        with self.assertRaises(ValueError): tc._json(b'{"number":NaN}')
        self.reply = None
        with self.assertRaises(ValueError): tc._http(snapshot, "/health/ready", time.monotonic() + 1, b"x" * ((1 << 20) + 1))

    def test_total_http_deadline_slow_headers(self):
        def drip(handler):
            try:
                for byte in b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n":
                    handler.connection.send(bytes([byte]))
                    time.sleep(0.03)
            except OSError:
                pass
        snapshot = self.serve(drip)
        start = time.monotonic()
        with self.assertRaises(Exception): tc._http(snapshot, "/health/ready", start + 0.15)
        self.assertLess(time.monotonic() - start, 0.7)

    def test_rediscovery_once_auth_and_instance_race(self):
        snapshot = self.endpoint()
        good = {"instance_id": INSTANCE}
        with patch.object(tc, "_http", side_effect=[tc._Race(), good]), patch.object(tc, "_discovery", return_value=snapshot) as discovery:
            self.assertEqual(tc._request(snapshot, "/x", time.monotonic() + 1, retry_budget=[1]), good)
            self.assertEqual(discovery.call_count, 1)
        with patch.object(tc, "_http", side_effect=tc._Race()), patch.object(tc, "_discovery", return_value=tc._Snapshot(12345, "c" * 64, TOKEN)):
            with self.assertRaises(ValueError): tc._request(snapshot, "/x", time.monotonic() + 1)
        budget = [0]
        with patch.object(tc, "_http", side_effect=tc._Race()), patch.object(tc, "_discovery") as discovery:
            with self.assertRaises(ValueError): tc._request(snapshot, "/x", time.monotonic() + 1, retry_budget=budget)
            discovery.assert_not_called()

    def test_input_utf8_serialized_bounds_no_truncation(self):
        self.fake_ready()
        embedder = tc.select_embedder(tc.EMBEDDING_MODEL)
        texts = ["🌊" * 16384] * 20
        self.assertEqual(len(list(embedder.embed(texts))), 20)
        bodies = [body for path, body in self.requests if path == "/v1/embeddings"]
        self.assertEqual([x for body in bodies for x in body["input"]], texts)
        self.assertTrue(all(len(tc._encoded(body)) <= tc.MAX_BODY_BYTES for body in bodies))
        self.assertGreater(len(bodies), 1)
        before = len(self.requests)
        with self.assertRaises(tc.TensorwellUnavailable): embedder.embed(["🌊" * 16385])
        self.assertEqual(len(self.requests), before)
        self.assertNotIn(TOKEN, str(tc.status_snapshot()))
        self.assertNotIn("🌊", str(tc.status_snapshot()))

    def test_item_count_bound_and_late_failure_yields_nothing(self):
        self.fake_ready()
        embedder = tc.select_embedder(tc.EMBEDDING_MODEL)
        self.assertEqual(len(list(embedder.embed(["text"] * 129))), 129)
        bodies = [body for path, body in self.requests if path == "/v1/embeddings"]
        self.assertEqual([len(body["input"]) for body in bodies], [128, 1])
        calls = 0
        def fail_second(path, body):
            nonlocal calls
            if path == "/v1/embeddings":
                calls += 1
                if calls == 2: raise RuntimeError("secret raw failure " + TOKEN)
        self.reply = fail_second
        with self.assertRaises(tc.TensorwellUnavailable) as failure:
            embedder.embed(["text"] * 129)
        self.assertNotIn(TOKEN, str(failure.exception))
        self.assertEqual(tc.status_snapshot()["reason"], "inference_unavailable")
        self.assertIsNone(tc.select_embedder(tc.EMBEDDING_MODEL))

    def test_invalid_response_count_index_dimension_finite_and_identity(self):
        self.fake_ready()
        mutations = [lambda r: r.update(data=[]), lambda r: r["data"][0].update(index=True),
                     lambda r: r["data"][0].update(index=1), lambda r: r["data"][0].update(embedding=[0]),
                     lambda r: r["data"][0]["embedding"].__setitem__(0, float("nan")),
                     lambda r: r["data"][0]["embedding"].__setitem__(0, True),
                     lambda r: r["model"].update(identity="sha256:" + "0" * 64)]
        for mutation in mutations:
            tc._pair, tc._cache_until, tc._backoff_until = None, 0, 0
            self.reply = None
            embedder = tc.select_embedder(tc.EMBEDDING_MODEL)
            good = self.answer(None, "/v1/embeddings", 0, tc._encoded({"input": [""]}))
            mutation(good)
            self.reply = lambda path, body: good
            with self.assertRaises(tc.TensorwellUnavailable): embedder.embed([""])

    def test_status_has_no_io_and_never_blocks_discovery(self):
        started, release = threading.Event(), threading.Event()
        def waiting(*args):
            started.set()
            release.wait(1)
            raise OSError
        with patch.object(tc, "_discovery", side_effect=waiting), patch.object(tc, "_cli") as cli:
            thread = threading.Thread(target=tc._qualified_pair)
            thread.start()
            self.assertTrue(started.wait(1))
            start = time.monotonic()
            tc.status_snapshot()
            self.assertLess(time.monotonic() - start, 0.15)
            release.set()
            thread.join(1)
            cli.assert_not_called()

    def test_availability_observation_is_not_selection_or_execution(self):
        initial = tc.status_snapshot()
        self.assertEqual(initial["availability"]["state"], "not_checked")
        self.assertIsNone(initial["availability"]["observed_at"])
        self.fake_ready()
        model = tc.select_embedder(tc.EMBEDDING_MODEL)
        first = tc.status_snapshot()
        self.assertEqual(first["reason"], "qualified_pair")
        self.assertEqual(first["availability"]["state"], "ready_compatible")
        self.assertIn("Both pinned models", first["availability"]["detail"])
        tc.observe_selection("query_embedding", model, "qualified_pair")
        self.assertIsNone(tc.inference_status_snapshot()["roles"]["query_embedding"]["last_success"])
        self.assertIs(tc._qualified_pair(), model._pair)
        self.assertEqual(tc.status_snapshot()["availability"]["observed_at"], first["availability"]["observed_at"])
        with patch.object(tc.time, "monotonic", return_value=tc._availability["observed_monotonic"] + tc.CACHE_SECONDS):
            self.assertTrue(tc.status_snapshot()["availability"]["stale"])
        # Precision exclusion is a local routing reason, not a failed service check.
        self.assertIsNone(tc.select_embedder(tc.EMBEDDING_MODEL, "int8"))
        self.assertEqual(tc.status_snapshot()["availability"], first["availability"])

    def test_selection_diagnostics_are_invocation_owned_and_keep_model_or_none_api(self):
        self.fake_ready()
        reason = {}
        service = tc.select_embedder(tc.EMBEDDING_MODEL, diagnostic=reason)
        self.assertIsNotNone(service)
        self.assertEqual(reason, {"reason": "qualified_pair"})
        self.assertIsNotNone(tc.select_reranker(tc.RERANKER_MODEL))
        compatible = tc.status_snapshot()["availability"]
        for name, precision, expected in (("other", "full", "unsupported_model"),
                                          (tc.EMBEDDING_MODEL, "int8", "index_precision_mismatch")):
            reason = {}
            self.assertIsNone(tc.select_embedder(name, precision, diagnostic=reason))
            self.assertEqual(reason["reason"], expected)
        self.assertEqual(tc.status_snapshot()["availability"], compatible)
        with patch.dict(os.environ, {"WAVEFOUNDRY_DISABLE_TENSORWELL": "1"}):
            policy = {}
            self.assertIsNone(tc.select_reranker(tc.RERANKER_MODEL, diagnostic=policy))
            self.assertEqual(policy["reason"], "disabled")
        self.assertEqual(reason["reason"], "index_precision_mismatch")
        for profiles, expected in (([], "incompatible_profiles"), (None, "discovery_unavailable")):
            tc._pair, tc._cache_until, tc._backoff_until = None, 0, 0
            self.models = profiles or []
            first, backed_off = {}, {}
            with patch.object(tc, "_discovery", side_effect=OSError) if profiles is None else contextlib.nullcontext():
                self.assertIsNone(tc.select_reranker(tc.RERANKER_MODEL, diagnostic=first))
            count = len(self.requests)
            self.assertIsNone(tc.select_reranker(tc.RERANKER_MODEL, diagnostic=backed_off))
            self.assertEqual(first["reason"], expected)
            self.assertEqual(backed_off["reason"], "discovery_backoff")
            self.assertEqual(len(self.requests), count)

    def test_attempt_order_success_provenance_and_detached_snapshots(self):
        local = SimpleNamespace(provider="CUDAExecutionProvider")
        service = SimpleNamespace(is_tensorwell=True)
        old = tc.attempt("search_reranking", local)
        newer = tc.attempt("search_reranking", service)
        tc.finish_attempt(newer, returned=False, accepted=False, reason="inference_failed")
        tc.finish_attempt(old, returned=True, accepted=True)
        role = tc.inference_status_snapshot()["roles"]["search_reranking"]
        self.assertEqual(role["last_attempt"]["sequence"], newer[2])
        self.assertEqual(role["last_attempt"]["provider"], "tensorwell")
        self.assertEqual(role["last_attempt"]["provider_outcome"], "failed")
        self.assertEqual(role["last_attempt"]["caller_outcome"], "degraded")
        self.assertEqual(role["last_attempt"]["reason"], "inference_failed")
        self.assertEqual(role["last_success"]["provider"], "in_process")
        self.assertEqual(role["last_success"]["accelerator"], "CUDAExecutionProvider")
        newest = tc.attempt("search_reranking", service)
        tc.provider_returned(newest)
        pending = tc.inference_status_snapshot()["roles"]["search_reranking"]["last_attempt"]
        self.assertEqual((pending["provider_outcome"], pending["caller_outcome"]), ("returned", "pending"))
        tc.finish_attempt(newest, returned=True, accepted=True)
        tc.finish_attempt(old, returned=True, accepted=True)
        snapshot = tc.inference_status_snapshot()
        self.assertEqual(snapshot["roles"]["search_reranking"]["last_success"]["sequence"], newest[2])
        snapshot["roles"]["search_reranking"]["last_success"]["provider"] = "corrupt"
        snapshot["local_models"]["docs_embedding"]["shared_with"].append("corrupt")
        self.assertEqual(tc.inference_status_snapshot()["roles"]["search_reranking"]["last_success"]["provider"], "tensorwell")
        self.assertNotIn("corrupt", tc.inference_status_snapshot()["local_models"]["docs_embedding"]["shared_with"])

    def test_reload_keeps_weak_ownership_but_invalidates_attempts(self):
        class Model:
            pass
        held = Model()
        tc.observe_owner("docs_embedding", held, tc.EMBEDDING_MODEL)
        token = tc.attempt("query_embedding", held)
        before = tc.inference_status_snapshot()
        with tc.process_hold_guard():
            importlib.reload(tc)
        after = tc.inference_status_snapshot()
        self.assertEqual(after["scope"]["pid"], before["scope"]["pid"])
        self.assertEqual(after["scope"]["observation_started_at"], before["scope"]["observation_started_at"])
        self.assertGreater(after["scope"]["epoch"], before["scope"]["epoch"])
        self.assertEqual(after["local_models"]["docs_embedding"]["state"], "loaded")
        tc.finish_attempt(token, returned=True, accepted=True)
        self.assertIsNone(tc.inference_status_snapshot()["roles"]["query_embedding"]["last_success"])
        del held
        self.assertEqual(tc.inference_status_snapshot()["local_models"]["docs_embedding"]["state"], "unknown")

    def test_changed_pid_never_adopts_inherited_observations(self):
        token = tc.attempt("query_embedding", SimpleNamespace(is_tensorwell=True))
        tc.finish_attempt(token, returned=True, accepted=True)
        with patch.object(tc.os, "getpid", return_value=tc._process_pid + 1000):
            snapshot = tc.inference_status_snapshot()
            self.assertIsNone(snapshot["roles"]["query_embedding"]["last_success"])
            self.assertTrue(all(row["state"] == "unknown" for row in snapshot["local_models"].values()))
            self.assertEqual(tc.status_snapshot()["availability"]["reason"], "process_changed")
            tc.finish_attempt(token, returned=True, accepted=True)
            self.assertIsNone(tc.inference_status_snapshot()["roles"]["query_embedding"]["last_success"])

    def test_ownership_is_bounded_shared_and_does_not_keep_models_alive(self):
        class Model:
            pass
        model = Model()
        for slot in ("search_reranking", "memory_reranking"):
            tc.observe_owner(slot, model, tc.RERANKER_MODEL)
        snapshot = tc.inference_status_snapshot()["local_models"]
        self.assertEqual(snapshot["search_reranking"]["shared_with"], ["memory_reranking"])
        del model
        self.assertEqual(tc.inference_status_snapshot()["local_models"]["search_reranking"]["state"], "not_loaded")
        self.assertEqual(len(tc._owners), 4)
        tc.observe_owner("docs_embedding", object(), tc.EMBEDDING_MODEL)
        self.assertEqual(tc.inference_status_snapshot()["local_models"]["docs_embedding"]["state"], "unknown")

    def test_discovery_contention_within_total_budget(self):
        tc._probe_lock.acquire()
        try:
            start = time.monotonic()
            self.assertIsNone(tc._qualified_pair(start + 0.04))
            self.assertLess(time.monotonic() - start, 0.2)
        finally:
            tc._probe_lock.release()

    def test_reload_generation_refuses_pending_publication_and_old_failure(self):
        self.fake_ready()
        initial = tc._generation
        sentinel = object()
        original_request = tc._request
        def reload_during_models(snapshot, path, deadline, body=None, retry_budget=None):
            value = original_request(snapshot, path, deadline, body, retry_budget)
            if path == "/v1/models":
                tc._generation += 1
                tc._pair, tc._cache_until, tc._backoff_until = sentinel, 123, 0
            return value
        with patch.object(tc, "_generation", initial), patch.object(tc, "_request", side_effect=reload_during_models):
            self.assertIsNone(tc._qualified_pair())
            self.assertIs(tc._pair, sentinel)
            self.assertEqual(tc._cache_until, 123)
            tc._failed(initial)
            self.assertIs(tc._pair, sentinel)
            self.assertEqual(tc._backoff_until, 0)
        tc._pair, tc._cache_until, tc._backoff_until = None, 0, 0
        adapter = tc.select_embedder(tc.EMBEDDING_MODEL)
        before = len(self.requests)
        with patch.object(tc, "_generation", tc._generation + 1):
            with self.assertRaises(tc.TensorwellUnavailable): adapter.embed(["stale selected operation"])
            self.assertEqual(len(self.requests), before, "stale adapters must fail before HTTP")
        def reload_during_inference(snapshot, path, deadline, body=None, retry_budget=None):
            value = original_request(snapshot, path, deadline, body, retry_budget)
            tc._generation += 1
            tc._pair, tc._cache_until, tc._backoff_until = sentinel, 123, 0
            return value
        with patch.object(tc, "_generation", tc._generation), patch.object(tc, "_request", side_effect=reload_during_inference):
            with self.assertRaises(tc.TensorwellUnavailable): adapter.embed(["raw"])
            self.assertIs(tc._pair, sentinel)
            self.assertEqual(tc._backoff_until, 0)

    def test_cli_exact_child_timeout_bounded_capture(self):
        executable = self.home / "controller"
        executable.write_text(f"#!{sys.executable}\nimport time\ntime.sleep(5)\n")
        executable.chmod(0o700)
        real_popen = subprocess.Popen
        owned = []
        def capture(*args, **kwargs):
            self.assertNotIn("start_new_session", kwargs)
            self.assertNotIn("process_group", kwargs)
            child = real_popen(*args, **kwargs)
            owned.append(child)
            return child
        sibling = real_popen([sys.executable, "-B", "-c", "import time;time.sleep(5)"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            with patch.object(tc.subprocess, "Popen", side_effect=capture):
                with self.assertRaises(TimeoutError): tc._cli(executable, ["status", "--json"], time.monotonic() + 0.4)
            self.assertIsNotNone(owned[0].returncode)
            self.assertIsNone(sibling.poll())
        finally:
            sibling.kill()
            sibling.wait(timeout=2)

    def test_cli_completed_child_output_limits(self):
        # Output semantics do not depend on starting another interpreter before
        # a deadline. The preceding test retains real process/thread coverage.
        class ImmediateReader:
            def __init__(self, *, target, args, daemon):
                self.target, self.args = target, args
            def start(self):
                self.target(*self.args)
            def join(self, timeout=None):
                pass
            def is_alive(self):
                return False

        class Stream(io.BytesIO):
            reached_eof = False
            def read(self, size=-1):
                part = super().read(size)
                if not part:
                    self.reached_eof = True
                return part

        for stream_index in (0, 1):
            for extra in (0, 1):
                with self.subTest(stream=stream_index, excess=extra):
                    payloads = [b"{}", b""]
                    prefix = payloads[stream_index]
                    payloads[stream_index] = prefix + b" " * (tc.CLI_OUTPUT_BYTES + extra - len(prefix))
                    streams = [Stream(payload) for payload in payloads]
                    buffers = []
                    class Capture(bytearray):
                        def __init__(self):
                            super().__init__()
                            buffers.append(self)
                    child = SimpleNamespace(stdout=streams[0], stderr=streams[1],
                                            returncode=0, wait=lambda timeout: 0)
                    with patch.object(tc.subprocess, "Popen", return_value=child), \
                         patch.object(tc.threading, "Thread", ImmediateReader), \
                         patch.object(tc, "bytearray", Capture, create=True):
                        if extra:
                            with self.assertRaisesRegex(ValueError, "controller unavailable"):
                                tc._cli(self.home / "controller", ["status", "--json"], time.monotonic() + 3)
                        else:
                            self.assertEqual(tc._cli(self.home / "controller", ["status", "--json"], time.monotonic() + 3), {})
                    self.assertEqual([len(buffer) for buffer in buffers],
                                     [min(len(payload), tc.CLI_OUTPUT_BYTES) for payload in payloads])
                    self.assertTrue(all(stream.closed and stream.reached_eof for stream in streams))

    def test_controlled_executable_lookup_and_hash(self):
        root = self.home / "repo"
        root.mkdir()
        bin_dir = self.home / "bin"
        bin_dir.mkdir()
        bad = root / "tensorwell"
        bad.write_text("unsafe")
        bad.chmod(0o700)
        linked = bin_dir / "tensorwell"
        linked.symlink_to(bad)
        with patch.dict(os.environ, {"PATH": f".:{root}:{bin_dir}"}):
            self.assertIsNone(tc._controller(root))
        linked.unlink()
        linked.write_text("qualified bytes")
        linked.chmod(0o700)
        with patch.dict(os.environ, {"PATH": str(bin_dir)}):
            self.assertEqual(tc._controller(root), linked.resolve())
        self.assertEqual(tc._controller_digest(linked, time.monotonic() + 1), hashlib.sha256(b"qualified bytes").hexdigest())
        oversized = self.home / "oversized"
        with oversized.open("wb") as file:
            file.truncate((64 << 20) + 1)
        with self.assertRaises(ValueError): tc._controller_digest(oversized, time.monotonic() + 2)
        with patch.object(tc.subprocess, "Popen") as popen:
            with self.assertRaises(ValueError): tc._cli(linked, [], time.monotonic() + 1, (0, 0, 0, 0, 0))
            popen.assert_not_called()
        linked.unlink()
        linked.symlink_to(bad)
        with self.assertRaises(OSError): tc._controller_digest(linked, time.monotonic() + 1)

    def test_start_once_ready_stopped_starting_failed_and_unknown(self):
        self.enterContext(patch.object(tc, "_controller_file_identity", return_value=(1, 2, 3, 4, 5)))
        pair = tc._Pair(tc._Snapshot(12345, INSTANCE, TOKEN), *self.models)
        cases = [("stopped", True), ("starting", False), ("failed", False), ("unavailable", False)]
        for state, should_start in cases:
            tc._status["startup"] = "scheduled"
            with patch.object(tc, "_qualified_pair", side_effect=[None, pair]), patch.object(tc, "_controller", return_value=Path("/fixture")), \
                 patch.object(tc, "_controller_digest", return_value=next(iter(tc.QUALIFIED_CONTROLLER_SHA256))), \
                 patch.object(tc, "_cli", side_effect=[{"status": state}, {"schema_version": 1, "outcome": "started", "code": None}]) as cli:
                tc._startup(self.home)
                self.assertEqual(cli.call_count, 2 if should_start else 1)
                if should_start: self.assertEqual(cli.call_args.args[1], ["start", "--json", "--no-menu"])
        with patch.object(tc, "_qualified_pair", return_value=pair), patch.object(tc, "_cli") as cli:
            tc._startup(self.home)
            cli.assert_not_called()
        with patch.object(tc, "_qualified_pair", return_value=None), patch.object(tc, "_controller", return_value=Path("/fixture")), \
             patch.object(tc, "_controller_digest", return_value="unknown"), patch.object(tc, "_cli") as cli:
            tc._startup(self.home)
            cli.assert_not_called()
            self.assertEqual(tc.status_snapshot()["reason"], "controller_unqualified")
        with patch.object(tc.threading, "Thread") as thread:
            tc.start_background(self.home)
            tc.start_background(self.home)
            self.assertEqual(thread.call_count, 1)

    def test_startup_uses_real_fixture_controller_and_preserves_configuration(self):
        executable = self.home / "controller"
        trace = self.home / "calls.jsonl"
        config = self.home / "config.toml"
        config.write_bytes(b"synthetic fixture configuration\n")
        before = config.read_bytes()
        executable.write_text(f"#!{sys.executable}\nimport json,sys\n"
                              f"with open({str(trace)!r},'a') as file: file.write(json.dumps(sys.argv[1:])+'\\n')\n"
                              "print(json.dumps({'status':'stopped'} if sys.argv[1]=='status' else "
                              "{'schema_version':1,'outcome':'started','code':None}))\n")
        executable.chmod(0o700)
        digest = hashlib.sha256(executable.read_bytes()).hexdigest()
        pair = tc._Pair(tc._Snapshot(12345, INSTANCE, TOKEN), *self.models)
        tc._status["startup"] = "scheduled"
        with patch.object(tc, "_controller", return_value=executable), \
             patch.object(tc, "QUALIFIED_CONTROLLER_SHA256", frozenset({digest})), \
             patch.object(tc, "_qualified_pair", side_effect=[None, pair]):
            tc._startup(self.home)
        self.assertEqual([json.loads(row) for row in trace.read_text().splitlines()],
                         [["status", "--json"], ["start", "--json", "--no-menu"]])
        self.assertEqual(tc.status_snapshot()["startup"], "ready")
        self.assertEqual(config.read_bytes(), before)
        tc._status["startup"] = "scheduled"
        with patch.object(tc, "STARTUP_SECONDS", 0.15), patch.object(tc, "_controller", return_value=executable), \
             patch.object(tc, "QUALIFIED_CONTROLLER_SHA256", frozenset({digest})), \
             patch.object(tc, "_qualified_pair", return_value=None), patch.object(tc, "_cli", return_value={"status": "starting"}) as cli:
            tc._startup(self.home)
            self.assertEqual(cli.call_count, 1)
            self.assertEqual(tc.status_snapshot()["reason"], "startup_timeout")
        tc._backoff_until = 0
        self.fake_ready()
        with patch.object(tc, "_cli", side_effect=AssertionError("no second startup")):
            self.assertIsNotNone(tc.select_embedder(tc.EMBEDDING_MODEL))


if __name__ == "__main__":
    unittest.main()
