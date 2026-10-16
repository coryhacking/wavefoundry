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


def capabilities(**updates):
    # Producer: service.rs capabilities and workers.rs adaptive declaration.
    value = {"schema_version": 2,
             "limits": {"max_items": 128, "max_body_bytes": 1048576, "max_text_bytes": 65536, "max_connections": 32},
             "timeouts": {"default_ms": 30000, "max_ms": 300000, "native_quantum_watchdog_ms": 330000,
                          "scope": "handler_entry_through_completion"},
             "workloads": {"supported": ["interactive", "batch"], "default": "interactive"},
             "timing": {"request_flag": "include_timing", "unit": "milliseconds", "rounding": "floor"},
             "scheduling": {"policy": "dedicated_adaptive", "max_pending": 8, "quantum": "profile_native_batch"},
             "profiles": [{"id": "arctic-fp16-coreml", "native_batch_items": 1024}],
             "adaptive": {"sample_ms": 250}}
    value.update(updates)
    if value["schema_version"] == 2 and "client_session" not in updates:
        value["client_session"] = {"header": "Client-Session-Id", "format": "uuid-shaped-ascii-8-4-4-4-12-hex",
                                   "optional": True, "authentication": False, "unknown": "excluded-from-diversity"}
    return value


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
        for key, value in (("_capability_cache", None), ("_pair", None), ("_cache_until", 0), ("_backoff_until", 0), ("_startup_scheduled", False), ("_startup_worker", None)):
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
        for key, value in (("_stats_until", 0), ("_stats", None), ("_stats_reason", "absent"), ("_timing", {}),
                           ("_timing_sequence", {}), ("_last_readiness_at", None),
                           ("_counters", dict.fromkeys(tc._counters, 0))):
            self.enterContext(patch.object(tc, key, value))
        if hasattr(tc._attempt_context, "token"):
            del tc._attempt_context.token
        self.models = [descriptor("embedding"), descriptor("reranking")]
        self.requests = []
        self.session_headers = []
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

    def answer(self, snapshot, path, deadline, body=None, **kwargs):
        value = json.loads(body) if body is not None else None
        self.requests.append((path, value))
        if self.reply is not None:
            result = self.reply(path, value)
            if result is not None:
                return result
        if path == "/v1/capabilities":
            return {"instance_id": INSTANCE, **capabilities()}
        if path == "/v1/stats":
            return {"instance_id": INSTANCE, "schema_version": 2, "models": [{"model": {"id": model["id"], "load_count": 1}, "optional_state": None} for model in reversed(self.models)]}
        if path == "/health/ready":
            return {"instance_id": INSTANCE, "status": "ready"}
        if path == "/v1/models":
            return {"instance_id": INSTANCE, "data": self.models}
        embedding = path == "/v1/embeddings"
        items = value["input" if embedding else "documents"]
        response = {"instance_id": INSTANCE, "model": descriptor("embedding" if embedding else "reranking"),
                    "data": [{"index": i, "embedding": [1.0] + [0.0] * 383} if embedding
                             else {"index": i, "score": float(i) - 2.5} for i, text in enumerate(items)]}
        if value.get("include_timing") is True:
            response["metadata"] = {"workload": value["workload"], "timing": {"queue_ms": 1, "execution_ms": 2, "total_ms": 3}}
        return response

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
                owner.session_headers.append((self.path, self.headers.get_all("Client-Session-Id")))
                owner.assertEqual(self.headers["Authorization"], "Bearer " + TOKEN)
                owner.assertEqual(self.headers["Host"], f"127.0.0.1:{owner.server.server_port}")
                if custom:
                    custom(self)
                    return
                try:
                    value = owner.answer(None, self.path, time.monotonic() + 1, body)
                    status = 200
                except tc._HTTPFailure as failure:
                    value = {"instance_id": INSTANCE, "error": {"code": failure.reason,
                             "retryable": False, "message": "fixture private message"}}
                    status = failure.status
                encoded = json.dumps(value).encode()
                self.send_response(status)
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

    def test_producer_capability_nested_consumed_fields_and_session_rejections(self):
        documents = []
        for container in ("limits", "timeouts", "workloads", "timing"):
            missing = capabilities()
            del missing[container]
            documents.append(missing)
            for bad in (None, [], "object", True):
                documents.append(capabilities(**{container: bad}))
        for container, key in (("limits", "max_items"), ("limits", "max_body_bytes"),
                               ("limits", "max_text_bytes"), ("timeouts", "max_ms"),
                               ("workloads", "supported"), ("timing", "request_flag"),
                               ("timing", "unit"), ("timing", "rounding")):
            document = capabilities()
            del document[container][key]
            documents.append(document)
        for key in ("max_items", "max_body_bytes", "max_text_bytes"):
            for bad in (True, 0, -1, 1.0, "128"):
                document = capabilities()
                document["limits"][key] = bad
                documents.append(document)
        for bad in (True, 0, 999, 300001, 10 ** 12, 1000.0):
            documents.append(capabilities(timeouts={"max_ms": bad}))
        for supported in (None, "interactive", ["interactive"], ["batch"], ["interactive", "batch", True],
                          ["interactive", "batch"] + ["extra"] * 7):
            documents.append(capabilities(workloads={"supported": supported}))
        for key, wrong in (("request_flag", "timing"), ("unit", "seconds"), ("rounding", "ceil")):
            document = capabilities()
            document["timing"][key] = wrong
            documents.append(document)
        absent = capabilities()
        del absent["client_session"]
        documents.append(absent)
        for bad in (None, [], "Client-Session-Id", True):
            documents.append(capabilities(client_session=bad))
        for key, wrong_values in (("header", ("Authorization", "client-session-id", "X-Custom")),
                                  ("format", ("uuid", None)), ("optional", (False, 1, "true", None)),
                                  ("authentication", (True, 0, "false", None))):
            missing = capabilities()
            del missing["client_session"][key]
            documents.append(missing)
            for wrong in wrong_values:
                document = capabilities()
                document["client_session"][key] = wrong
                documents.append(document)
        documents += [{"schema": 2, "max_timeout_ms": 300000, "max_items": 128, "max_body_bytes": 1048576,
                       "max_input_bytes": 65536, "workloads": ["interactive", "batch"], "client_session_hint": True},
                      capabilities(schema_version=True), capabilities(schema_version=3)]
        for document in documents:
            with self.subTest(capability=document):
                with self.assertRaises(tc._CapabilitiesUnsupported): tc._capabilities(document)
        # A schema-one service cannot opt this client into a session extension.
        self.assertFalse(tc._capabilities(capabilities(schema_version=1, client_session={"header": "Authorization"}))["client_session_hint"])

    def test_producer_schema_session_headers_stable_across_retry_and_roles(self):
        self.serve()
        for schema in (1, 2):
            with self.subTest(schema=schema):
                tc._pair, tc._cache_until, tc._backoff_until, tc._capability_cache, tc._stats_until = None, 0, 0, None, 0
                posts = [0]
                def reply(path, body):
                    if path == "/v1/capabilities":
                        return {"instance_id": INSTANCE, **capabilities(schema_version=schema)}
                    if body is not None:
                        posts[0] += 1
                        if posts[0] == 1:
                            raise tc._HTTPFailure(401)
                self.reply = reply
                start = len(self.session_headers)
                embedder = tc.select_embedder(tc.EMBEDDING_MODEL)
                self.assertIsNotNone(embedder)
                embedder.embed_query("generic query")
                tc.select_reranker(tc.RERANKER_MODEL).rerank("generic query", ["generic passage"])
                hints = [hints for path, hints in self.session_headers[start:] if path in {"/v1/embeddings", "/v1/rerank"}]
                self.assertEqual(len(hints), 3)
                if schema == 1:
                    self.assertEqual(hints, [None] * 3)
                else:
                    self.assertTrue(all(hint is not None and len(hint) == 1 for hint in hints))
                    self.assertEqual(hints[0], hints[1])
                    self.assertEqual(hints[0], hints[2])
                    self.assertRegex(hints[0][0], r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
                    self.assertNotIn(hints[0][0], repr(tc.status_bundle_snapshot()))
                self.assertEqual(tc._pair.capabilities["client_session_hint"], schema == 2)

    def test_producer_nested_capabilities_normalize_schema_one_and_two(self):
        for schema in (1, 2):
            with self.subTest(schema=schema):
                document = capabilities(schema_version=schema)
                document["limits"].update(max_items=1024, max_body_bytes=2 << 20, max_text_bytes=128 << 10)
                try:
                    normalized = tc._capabilities(document)
                except tc._CapabilitiesUnsupported:
                    self.fail("Producer-shaped nested capabilities were rejected")
                self.assertEqual(normalized, {"schema": schema, "max_timeout_ms": 300000, "max_items": 128,
                    "max_body_bytes": 1048576, "max_input_bytes": 65536, "client_session_hint": schema == 2})
                document["timeouts"]["max_ms"] = 1000
                self.assertEqual(tc._capabilities(document)["max_timeout_ms"], 1000)

    def test_producer_nested_timing_normalizes_without_flat_wire_alias(self):
        valid = {"metadata": {"workload": "interactive", "timing": {"queue_ms": 1, "execution_ms": 2, "total_ms": 3}}}
        try:
            tc._response_timing(valid, "interactive", "query_embedding")
        except ValueError:
            self.fail("Producer-shaped nested timing was rejected")
        expected = {"workload": "interactive", "queue_ms": 1, "execution_ms": 2, "total_ms": 3}
        self.assertEqual(tc.status_snapshot()["timing"]["query_embedding"], expected)
        malformed = [{"metadata": None}, {"metadata": []}, {"metadata": {"workload": "interactive"}},
                     {"metadata": {"workload": "interactive", "timing": []}},
                     {"metadata": {"workload": "interactive", "queue_ms": 1, "execution_ms": 2, "total_ms": 3}}]
        for field in ("queue_ms", "execution_ms", "total_ms"):
            for bad in (True, "1", -1, float("nan"), 1 << 31):
                value = copy.deepcopy(valid)
                value["metadata"]["timing"][field] = bad
                malformed.append(value)
            value = copy.deepcopy(valid)
            del value["metadata"]["timing"][field]
            malformed.append(value)
        value = copy.deepcopy(valid)
        value["metadata"]["workload"] = "batch"
        malformed.append(value)
        for value in malformed:
            with self.subTest(metadata=value):
                with self.assertRaises(ValueError): tc._response_timing(value, "interactive", "query_embedding")
                self.assertEqual(tc.status_snapshot()["timing"]["query_embedding"], expected)

    def test_producer_stats_nested_counts_and_nullable_labels(self):
        self.fake_ready()
        pair = tc._Pair(self.endpoint(), *self.models, generation=tc._generation)
        tc._pair = pair
        tc._status["backend"] = "tensorwell"
        rows = [{"model": {"id": "minilm-fp16-coreml", "load_count": 7}, "optional_state": None,
                 "suppression_reason": None, "resident_sessions": 1},
                {"model": {"id": "arctic-fp16-coreml", "load_count": 13, "secret": TOKEN},
                 "optional_state": "resident", "known_clients_active": 2, "known_clients_queued": 3}]
        document = {"instance_id": INSTANCE, "schema_version": 3, "models": rows, "suppression_reason": "global_only"}
        self.reply = lambda path, body: document if path == "/v1/stats" else None
        tc._refresh_stats(pair)
        result = tc.status_snapshot()["stats"]
        self.assertIsNotNone(result, "Null optional row labels must not invalidate valid statistics")
        self.assertEqual(result["models"], {"minilm-fp16-coreml": {"load_count": 7, "resident_sessions": 1},
            "arctic-fp16-coreml": {"load_count": 13, "optional_state": "resident", "known_clients_active": 2, "known_clients_queued": 3}})
        self.assertNotIn("global_only", repr(result))
        self.assertNotIn(TOKEN, repr(result))
        for row in rows:
            row.pop("optional_state", None)
            row.pop("suppression_reason", None)
            row["load_count"] = 999  # Provisional row-level count is unknown wire data.
        tc._stats_until = 0
        tc._refresh_stats(pair)
        self.assertEqual(tc.status_snapshot()["stats"]["models"]["arctic-fp16-coreml"]["load_count"], 13)
        for field in ("load_count", "optional_state", "suppression_reason"):
            for bad in ((True, -1, 1 << 53, "1", None) if field == "load_count" else (True, 1, "A", "x" * 65)):
                with self.subTest(field=field, bad=bad):
                    target = rows[0]["model"] if field == "load_count" else rows[0]
                    original = copy.deepcopy(target)
                    target[field] = bad
                    tc._stats_until = 0
                    tc._refresh_stats(pair)
                    self.assertIsNone(tc.status_snapshot()["stats"])
                    self.assertIs(tc._pair, pair)
                    target.clear()
                    target.update(original)

    def test_public_operations_reject_validation_that_finishes_after_deadline(self):
        self.fake_ready()
        for entrypoint in ("embed", "embed_query", "rerank"):
            for seam in ("_descriptor", "_response_timing"):
                for completed_at in (100.5, 101.0, 102.0):
                    with self.subTest(entrypoint=entrypoint, seam=seam, completed_at=completed_at):
                        tc._pair, tc._cache_until, tc._backoff_until = None, 0, 0
                        model = (tc.select_reranker(tc.RERANKER_MODEL) if entrypoint == "rerank"
                                 else tc.select_embedder(tc.EMBEDDING_MODEL))
                        original = getattr(tc, seam)
                        clock = [100.0]
                        published = []
                        def validation(*args, **kwargs):
                            result = original(*args, **kwargs)
                            clock[0] = completed_at
                            return result
                        def invoke():
                            if entrypoint == "embed":
                                published.extend(model.embed(["raw document"]))
                            elif entrypoint == "embed_query":
                                published.append(model.embed_query("raw query"))
                            else:
                                published.extend(model.rerank("raw query", ["raw document"]))
                        with patch.object(tc.time, "monotonic", side_effect=lambda: clock[0]), \
                             patch.object(tc, "BATCH_SECONDS", 1.0), patch.object(tc, "INFERENCE_SECONDS", 1.0), \
                             patch.object(tc, "DELIVERY_MARGIN_SECONDS", 0.0), \
                             patch.object(tc, "_counters", dict.fromkeys(tc._counters, 0)), \
                             patch.object(tc, seam, side_effect=validation):
                            if completed_at >= 101.0:
                                with self.assertRaises(tc.TensorwellUnavailable) as failure:
                                    invoke()
                                self.assertEqual(failure.exception.reason, "deadline_exceeded")
                                self.assertEqual(failure.exception.diagnostic["phase"], "response_validation")
                                self.assertIs(tc._pair, model._pair)
                                self.assertEqual(tc._counters["deadline_exceeded"], 1)
                                self.assertEqual(published, [])
                                self.assertEqual(tc._counters["succeeded"], 0)
                            else:
                                invoke()
                                self.assertEqual(len(published), 1)
                                self.assertEqual(tc._counters["succeeded"], 1)
                            self.assertEqual(tc._counters["offered"], 1)
                        # Every deadline failure must relinquish admission.
                        self.assertTrue(tc._batch_lock.acquire(blocking=False))
                        tc._batch_lock.release()
                        acquired = []
                        try:
                            for _ in range(tc.INTERACTIVE_LIMIT):
                                available = tc._interactive_slots.acquire(blocking=False)
                                if available:
                                    acquired.append(True)
                                self.assertTrue(available)
                        finally:
                            for _ in acquired:
                                tc._interactive_slots.release()

    def test_safe_selection_diagnostics_capability_readiness_and_discovery_phases(self):
        self.fake_ready()
        hint = tc._client_session_hint()
        for failed_path, status, code, expected in (
                ("/v1/capabilities", 404, None, {"reason": "capabilities_unsupported", "phase": "capabilities", "status": 404}),
                ("/v1/capabilities", 400, "invalid_request", {"reason": "capabilities_unsupported", "phase": "capabilities", "status": 400, "code": "invalid_request"}),
                ("/health/ready", 503, "service_unavailable", {"reason": "discovery_unavailable", "phase": "readiness", "status": 503, "code": "service_unavailable"})):
            with self.subTest(path=failed_path, status=status):
                tc._pair, tc._cache_until, tc._backoff_until, tc._capability_cache = None, 0, 0, None
                def failure(path, body):
                    if path == failed_path:
                        raise tc._HTTPFailure(status, code=code)
                self.reply = failure
                diagnostic = {}
                self.assertIsNone(tc.select_embedder(tc.EMBEDDING_MODEL, diagnostic=diagnostic))
                self.assertEqual(diagnostic, expected)
                self.assertNotIn(TOKEN, repr(diagnostic))
                self.assertNotIn(hint, repr(diagnostic))
        tc._pair, tc._cache_until, tc._backoff_until, tc._capability_cache = None, 0, 0, None
        diagnostic = {}
        with patch.object(tc, "_discovery", side_effect=ValueError("raw private path " + TOKEN + hint)):
            self.assertIsNone(tc.select_embedder(tc.EMBEDDING_MODEL, diagnostic=diagnostic))
        self.assertEqual(diagnostic, {"reason": "discovery_unavailable", "phase": "discovery"})
        self.assertNotIn(TOKEN, repr(diagnostic))
        self.assertNotIn(hint, repr(diagnostic))
        safe = tc._CapabilitiesUnsupported(status="503", code=TOKEN)
        self.assertEqual(vars(safe), {"status": None, "code": None})
        self.assertNotIn(TOKEN, str(safe))
        self.assertNotIn(hint, str(safe))

    def test_real_stats_schema_versions_array_identity_and_duplicates(self):
        self.serve()
        rows = [{"model": {"id": model["id"]}, "resident_sessions": i + 1} for i, model in enumerate(reversed(self.models))]
        document = {"instance_id": INSTANCE, "schema_version": 2, "models": rows + [{"model": {"id": "unknown"}, "load_count": -1}]}
        self.reply = lambda path, body: document if path == "/v1/stats" else None
        model = tc.select_embedder(tc.EMBEDDING_MODEL)
        self.assertIsNotNone(model)
        for schema in (2, 3):
            document["schema_version"] = schema
            tc._stats_until = 0
            tc._refresh_stats(model._pair)
            result = tc.status_snapshot()["stats"]
            self.assertEqual(result["schema_version"], schema)
            self.assertEqual(result["models"], {"arctic-fp16-coreml": {"resident_sessions": 2},
                                                 "minilm-fp16-coreml": {"resident_sessions": 1}})
        document["models"].append(copy.deepcopy(rows[0]))
        tc._stats_until = 0
        tc._refresh_stats(model._pair)
        self.assertIsNone(tc.status_snapshot()["stats"])
        self.assertEqual(tc.status_snapshot()["stats_reason"], "invalid")
        self.assertIsNotNone(tc._pair)

    def test_capabilities_http_absent_and_malformed_document(self):
        self.serve()
        for outcome in (tc._HTTPFailure(404), ["malformed"]):
            tc._pair, tc._cache_until, tc._backoff_until, tc._capability_cache = None, 0, 0, None
            def capability_reply(path, body):
                if path == "/v1/capabilities":
                    if isinstance(outcome, Exception): raise outcome
                    return outcome
            self.reply = capability_reply
            self.assertIsNone(tc.select_embedder(tc.EMBEDDING_MODEL))
            self.assertEqual(tc.status_snapshot()["reason"], "capabilities_unsupported")
            self.assertFalse(any(body is not None for path, body in self.requests))

    def test_old_instance_failure_cannot_deselect_new_qualified_instance(self):
        self.fake_ready()
        old = tc.select_embedder(tc.EMBEDDING_MODEL)
        entered, release = threading.Event(), threading.Event()
        errors = []
        newer = tc._Snapshot(old._pair.snapshot.port, "c" * 64, TOKEN)
        def response(snapshot, path, deadline, body=None, **kwargs):
            if body is not None and snapshot.instance == INSTANCE:
                entered.set()
                release.wait(2)
                raise tc._HTTPFailure(418)
            value = self.answer(snapshot, path, deadline, body)
            value["instance_id"] = snapshot.instance
            return value
        def invoke():
            try: old.embed_query("old pending input")
            except BaseException as failure: errors.append(failure)
        with patch.object(tc, "_http", side_effect=response):
            worker = threading.Thread(target=invoke)
            worker.start()
            self.assertTrue(entered.wait(1))
            tc._cache_until = 0
            with patch.object(tc, "_discovery", return_value=newer):
                current = tc.select_embedder(tc.EMBEDDING_MODEL)
            self.assertIsNotNone(current)
            self.assertEqual(current._pair.snapshot.instance, newer.instance)
            release.set()
            worker.join(2)
            self.assertFalse(worker.is_alive())
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].reason, "unexpected_response")
        self.assertIs(tc._pair, current._pair)
        self.assertEqual(tc.status_snapshot()["reason"], "qualified_pair")
        self.assertIs(tc.select_embedder(tc.EMBEDDING_MODEL)._pair, current._pair)

    def test_error_response_contradictory_instance_never_retries(self):
        calls = []
        def handler(request):
            calls.append(request.path)
            payload = json.dumps({"instance_id": "c" * 64, "error": {"code": "overloaded", "retryable": True}}).encode()
            request.send_response(429)
            request.send_header("Content-Type", "application/json")
            request.send_header("Content-Length", str(len(payload)))
            request.end_headers()
            request.wfile.write(payload)
        snapshot = self.serve(handler)
        with self.assertRaises(tc.TensorwellUnavailable) as failure:
            tc._request(snapshot, "/x", time.monotonic() + 1, b"{}", workload="interactive")
        self.assertEqual(failure.exception.reason, "unexpected_response")
        self.assertEqual(calls, ["/x"])

    def test_interactive_smaller_negotiated_deadline_and_safe_role_timing_order(self):
        self.fake_ready()
        self.reply = lambda path, body: {"instance_id": INSTANCE, **capabilities(timeouts={"max_ms": 1000})} if path == "/v1/capabilities" else None
        model = tc.select_embedder(tc.EMBEDDING_MODEL)
        model.embed_query("raw")
        self.assertEqual([body for path, body in self.requests if body is not None][-1]["timeout_ms"], 1000)
        before = tc.attempt("memory_reranking", model)
        after = tc.attempt("memory_reranking", model)
        metadata = {"metadata": {"workload": "interactive", "timing": {"queue_ms": 1, "execution_ms": 2, "total_ms": 3}}}
        tc._response_timing(metadata, "interactive", "memory_reranking", after)
        metadata["metadata"]["timing"]["total_ms"] = 99
        tc._response_timing(metadata, "interactive", "memory_reranking", before)
        self.assertEqual(tc.status_snapshot()["timing"]["memory_reranking"]["total_ms"], 3)
        tc.finish_attempt(after, returned=True, accepted=True)

    def test_inference_connect_timeout_and_dribbling_response_watchdog(self):
        snapshot = self.serve()
        constructor = tc.http.client.HTTPConnection
        observed = []
        def connection(*args, **kwargs):
            observed.append(kwargs["timeout"])
            return constructor(*args, **kwargs)
        with patch.object(tc.http.client, "HTTPConnection", side_effect=connection), patch.object(tc, "DISCOVERY_SECONDS", 0.25):
            body = tc._encoded({"input": ["raw"]})
            tc._http(snapshot, "/v1/embeddings", time.monotonic() + 2, body)
        self.assertEqual(observed, [0.25])
        self.server.shutdown()
        def drip(handler):
            data = b'{"instance_id":"' + INSTANCE.encode() + b'","data":[]}'
            handler.send_response(200)
            handler.send_header("Content-Type", "application/json")
            handler.send_header("Content-Length", str(len(data)))
            handler.end_headers()
            try:
                for byte in data:
                    handler.wfile.write(bytes([byte]))
                    handler.wfile.flush()
                    time.sleep(0.02)
            except OSError:
                pass
        snapshot = self.serve(drip)
        start = time.monotonic()
        with self.assertRaises(Exception):
            tc._http(snapshot, "/v1/embeddings", start + 0.08, b"{}")
        self.assertLess(time.monotonic() - start, 0.4)

    def test_real_error_body_parser_and_size_cap(self):
        state = {"body": b'{"error":{"code":"overloaded","code":"payload_rejected","retryable":true}}', "size": None}
        def handler(request):
            request.send_response(429)
            request.send_header("Content-Type", "application/json")
            request.send_header("Content-Length", str(state["size"] or len(state["body"])))
            request.end_headers()
            try: request.wfile.write(state["body"])
            except OSError: pass
        snapshot = self.serve(handler)
        with self.assertRaises(tc._HTTPFailure) as failed:
            tc._http(snapshot, "/x", time.monotonic() + 1, b"{}")
        self.assertEqual(failed.exception.reason, "overloaded")
        self.assertIsNone(failed.exception.code)
        state["size"] = tc.MAX_RESPONSE_BYTES + 1
        with self.assertRaisesRegex(ValueError, "large response"):
            tc._http(snapshot, "/x", time.monotonic() + 1, b"{}")

    def test_http_error_envelope_allowlist_and_message_discard(self):
        state = {"status": 429, "body": {"error": {"code": "payload_rejected", "retryable": True, "message": "SECRET INPUT " + TOKEN}}}
        def handler(request):
            payload = json.dumps(state["body"]).encode()
            request.send_response(state["status"])
            request.send_header("Content-Type", "application/json")
            request.send_header("Content-Length", str(len(payload)))
            request.send_header("Retry-After", "2")
            request.end_headers()
            request.wfile.write(payload)
        snapshot = self.serve(handler)
        for code, expected in (("payload_rejected", "payload_rejected"), ("not_documented", "overloaded"),
                               ("A" * 100000, "overloaded"), ("overloaded", "overloaded")):
            state["body"]["error"]["code"] = code
            with self.assertRaises(tc._HTTPFailure) as failure:
                tc._http(snapshot, "/x", time.monotonic() + 1, b"{}")
            self.assertEqual(failure.exception.reason, expected)
            self.assertNotIn("SECRET", repr(vars(failure.exception)))
            self.assertNotIn(TOKEN, repr(vars(failure.exception)))
        state["body"]["error"]["retryable"] = "true"
        with self.assertRaises(tc._HTTPFailure) as failure:
            tc._http(snapshot, "/x", time.monotonic() + 1, b"{}")
        self.assertIsNone(failure.exception.code)

    def test_failure_vocabulary_counters_retained_pair_and_attempt_reason(self):
        self.fake_ready()
        self.enterContext(patch.object(tc, "OVERLOAD_FLOOR_SECONDS", 0.001))
        self.enterContext(patch.object(tc, "OVERLOAD_JITTER_SECONDS", 0))
        self.enterContext(patch.object(tc, "UNAVAILABLE_BACKOFF_SECONDS", (0.001, 0.002)))
        for status, expected in ((429, "overloaded"), (504, "deadline_exceeded"), (503, "service_unavailable"),
                                 (400, "invalid_request"), (401, "unauthorized"), (404, "model_not_found"),
                                 (408, "request_timeout"), (413, "payload_rejected"), (415, "payload_rejected"), (418, "unexpected_response")):
            with self.subTest(status=status):
                tc._pair, tc._cache_until, tc._backoff_until = None, 0, 0
                self.reply = None
                model = tc.select_embedder(tc.EMBEDDING_MODEL)
                token = tc.attempt("query_embedding", model)
                request_count = len([body for path, body in self.requests if body is not None])
                def failure(path, body):
                    if body is not None:
                        raise tc._HTTPFailure(status)
                self.reply = failure
                with self.assertRaises(tc.TensorwellUnavailable) as failed:
                    model.embed_query("PRIVATE INPUT")
                self.assertEqual(failed.exception.reason, expected)
                self.assertEqual(failed.exception.diagnostic["reason"], expected)
                self.assertEqual(failed.exception.diagnostic["status"], status)
                self.assertEqual(tc.status_snapshot()["reason"], expected)
                tc.finish_attempt(token, returned=False, accepted=False, reason="service_failed_generic")
                self.assertEqual(tc.inference_status_snapshot()["roles"]["query_embedding"]["last_attempt"]["reason"], expected)
                self.assertEqual(tc._pair is None, expected in tc._DESELECT)
                if expected in {"invalid_request", "model_not_found", "request_timeout", "payload_rejected", "unexpected_response", "deadline_exceeded"}:
                    self.assertEqual(len([body for path, body in self.requests if body is not None]) - request_count, 1)
                self.assertNotIn("PRIVATE", repr(tc.status_bundle_snapshot()))
        self.assertEqual(tc.status_snapshot()["counters"], {"offered": 10, "succeeded": 0, "overloaded": 1,
            "deadline_exceeded": 1, "unavailable": 3, "transport_uncertain": 0, "rejected": 5, "cancelled": 0})

    def test_retry_table_attempt_caps_and_deadlines(self):
        snapshot = self.endpoint()
        self.enterContext(patch.object(tc, "OVERLOAD_FLOOR_SECONDS", 0.01))
        self.enterContext(patch.object(tc, "OVERLOAD_CEILING_SECONDS", 0.03))
        self.enterContext(patch.object(tc, "OVERLOAD_JITTER_SECONDS", 0))
        self.enterContext(patch.object(tc, "DEADLINE_BACKOFF_SECONDS", 0.01))
        self.enterContext(patch.object(tc, "UNAVAILABLE_BACKOFF_SECONDS", (0.01, 0.02)))
        for status, workload, attempts in ((429, "batch", 4), (504, "interactive", 1), (504, "batch", 2),
                                           (503, "batch", 3), (400, "batch", 1), (404, "batch", 1),
                                           (408, "batch", 1), (413, "batch", 1), (415, "batch", 1)):
            with self.subTest(status=status, workload=workload):
                calls, sleeps = [], []
                def response(snapshot, path, deadline, body=None, **kwargs):
                    calls.append(path)
                    if body is None:
                        return {"status": "ready"}
                    raise tc._HTTPFailure(status, retry_after="2")
                with patch.object(tc, "_http", side_effect=response), patch.object(tc.time, "sleep", side_effect=sleeps.append):
                    with self.assertRaises(tc.TensorwellUnavailable):
                        tc._request(snapshot, "/x", time.monotonic() + 1, b"{}", workload=workload)
                self.assertEqual(calls.count("/x"), attempts)
                if status == 429:
                    self.assertEqual(sleeps, [0.03] * 3)
                if status == 503:
                    self.assertEqual(calls.count("/health/ready"), 2)
        for retry_after in ("Wed, 21 Oct 2015 07:28:00 GMT", "-1", "garbage", None):
            sleeps = []
            with patch.object(tc, "_http", side_effect=tc._HTTPFailure(429, retry_after=retry_after)), patch.object(tc.time, "sleep", side_effect=sleeps.append):
                with self.assertRaises(tc.TensorwellUnavailable):
                    tc._request(snapshot, "/x", time.monotonic() + 1, b"{}", workload="batch")
            self.assertEqual(sleeps, [0.01] * 3)
        with patch.object(tc, "_http", side_effect=tc._HTTPFailure(429)) as http, patch.object(tc.time, "sleep") as sleep:
            with self.assertRaises(tc.TensorwellUnavailable) as failed:
                tc._request(snapshot, "/x", time.monotonic() + 0.001, b"{}", workload="batch")
            self.assertEqual(failed.exception.reason, "overloaded")
            self.assertEqual(http.call_count, 1)
            sleep.assert_not_called()
        with patch.object(tc, "_http", side_effect=[tc._HTTPFailure(429), tc._HTTPFailure(503), {"status": "ready"}, tc._HTTPFailure(429), tc._HTTPFailure(503)]) as http, patch.object(tc.time, "sleep"):
            with self.assertRaises(tc.TensorwellUnavailable):
                tc._request(snapshot, "/x", time.monotonic() + 1, b"{}", workload="batch")
            self.assertEqual(http.call_count, 5)  # four inference attempts plus readiness

    def test_transport_same_instance_only_one_rediscovery_and_cancelled(self):
        self.fake_ready()
        model = tc.select_embedder(tc.EMBEDDING_MODEL)
        snapshot = model._pair.snapshot
        good = self.answer(None, "/v1/embeddings", 0, tc._encoded({"input": ["x"]}))
        for changed, expected_calls in ((False, 2), (True, 1)):
            rotated = tc._Snapshot(snapshot.port, "c" * 64 if changed else INSTANCE, TOKEN)
            with patch.object(tc, "_http", side_effect=[ConnectionResetError(), good]) as http, patch.object(tc, "_discovery", return_value=rotated) as discovery:
                if changed:
                    with self.assertRaises(tc.TensorwellUnavailable) as error: model.embed_query("x")
                    self.assertEqual(error.exception.reason, "transport_uncertain")
                else:
                    self.assertEqual(model.embed_query("x")[0], 1)
                self.assertEqual(http.call_count, expected_calls)
                self.assertEqual(discovery.call_count, 1)
        with patch.object(tc, "_http", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt): model.embed_query("x")
        self.assertEqual(tc.status_snapshot()["counters"]["cancelled"], 1)
        self.assertTrue(tc._interactive_slots.acquire(blocking=False))
        tc._interactive_slots.release()

    def test_stats_safe_cached_and_failure_never_deselects(self):
        self.fake_ready()
        model = tc.select_embedder(tc.EMBEDDING_MODEL)
        first = tc.status_snapshot()
        self.assertIsNotNone(first["last_readiness_at"])
        self.assertEqual(first["stats"]["models"]["arctic-fp16-coreml"], {"load_count": 1})
        before = len(self.requests)
        with patch.object(tc, "_http", side_effect=AssertionError("status does I/O")):
            tc.status_snapshot(); tc.status_bundle_snapshot()
        self.assertEqual(len(self.requests), before)
        for outcome, reason in ((tc._HTTPFailure(404), "absent"), (OSError(), "invalid"),
                                ({"schema_version": 2, "models": {}}, "invalid"),
                                ({"schema_version": True, "models": []}, "invalid")):
            tc._stats_until = 0
            with patch.object(tc, "_http", side_effect=outcome if isinstance(outcome, Exception) else None,
                              return_value=outcome if isinstance(outcome, dict) else None):
                tc._refresh_stats(model._pair)
            self.assertIs(tc._pair, model._pair)
            self.assertIsNone(tc.status_snapshot()["stats"])
            self.assertEqual(tc.status_snapshot()["stats_reason"], reason)
        safe = {"schema_version": 3, "models": [{"model": {"id": m["id"], "load_count": 4}, "known_clients_active": 2,
                    "known_clients_queued": 3, "optional_state": "resident", "secret": TOKEN} for m in reversed(self.models)] +
                    [{"model": {"id": "unrelated-profile"}, "load_count": -999, "secret": TOKEN}], "secret": TOKEN}
        tc._stats_until = 0
        with patch.object(tc, "_http", return_value=safe) as http:
            tc._refresh_stats(model._pair); tc._refresh_stats(model._pair)
            self.assertEqual(http.call_count, 1)
        snapshot = tc.status_snapshot()
        self.assertNotIn(TOKEN, repr(snapshot))
        snapshot["stats"]["models"]["arctic-fp16-coreml"]["load_count"] = 999
        self.assertEqual(tc.status_snapshot()["stats"]["models"]["arctic-fp16-coreml"]["load_count"], 4)
        duplicate = copy.deepcopy(safe)
        duplicate["models"].append(copy.deepcopy(duplicate["models"][0]))
        tc._stats_until = 0
        with patch.object(tc, "_http", return_value=duplicate): tc._refresh_stats(model._pair)
        self.assertIsNone(tc.status_snapshot()["stats"])
        for field, value in (("load_count", True), ("load_count", 1 << 53), ("load_count", -1),
                             ("optional_state", "A"), ("suppression_reason", "x" * 65)):
            target = safe["models"][1]["model"] if field == "load_count" else safe["models"][1]
            target[field] = value
            tc._stats_until = 0
            with patch.object(tc, "_http", return_value=safe): tc._refresh_stats(model._pair)
            self.assertIsNone(tc.status_snapshot()["stats"])
            target.pop(field)

    def test_concurrency_limits_batch_separate_interactive_and_slot_deadline(self):
        self.fake_ready()
        model = tc.select_embedder(tc.EMBEDDING_MODEL)
        release, batch_entered, interactive_entered = threading.Event(), threading.Event(), threading.Event()
        counts = {"batch": 0, "interactive": 0}
        maxima = dict(counts)
        guard = threading.Lock()
        errors = []
        def response(snapshot, path, deadline, body=None, **kwargs):
            value = json.loads(body)
            workload = value["workload"]
            with guard:
                counts[workload] += 1
                maxima[workload] = max(maxima[workload], counts[workload])
                if workload == "batch": batch_entered.set()
                if counts["interactive"] == 4: interactive_entered.set()
            release.wait(2)
            with guard: counts[workload] -= 1
            return self.answer(snapshot, path, deadline, body)
        def invoke(batch=False):
            try:
                if batch: list(model.embed(["x"]))
                else: model.embed_query("x")
            except BaseException as error: errors.append(error)
        with patch.object(tc, "_http", side_effect=response), patch.object(tc, "INFERENCE_SECONDS", 0.10), patch.object(tc, "DELIVERY_MARGIN_SECONDS", 0.05):
            threads = [threading.Thread(target=invoke, args=(True,)) for _ in range(2)]
            for worker in threads: worker.start()
            self.assertTrue(batch_entered.wait(1))
            interactive = [threading.Thread(target=invoke) for _ in range(5)]
            for worker in interactive: worker.start()
            self.assertTrue(interactive_entered.wait(1), "interactive capacity must not wait for batch")
            time.sleep(0.18)
            self.assertTrue(any(isinstance(error, tc.TensorwellUnavailable) and error.reason == "overloaded" for error in errors))
            self.assertEqual(maxima, {"batch": 1, "interactive": 4})
            self.assertEqual(len([body for path, body in self.requests if body is not None]), 0)
            release.set()
            for worker in threads + interactive: worker.join(2)
            self.assertTrue(all(not worker.is_alive() for worker in threads + interactive))
        self.assertEqual(maxima, {"batch": 1, "interactive": 4})

    def test_per_request_watchdog_connect_timeout_and_session_reload(self):
        self.fake_ready()
        model = tc.select_embedder(tc.EMBEDDING_MODEL)
        deadlines = []
        original = tc._http
        def timed(snapshot, path, deadline, body=None, **kwargs):
            deadlines.append(deadline - time.monotonic())
            time.sleep(0.025)
            return original(snapshot, path, deadline, body, **kwargs)
        with patch.object(tc, "BATCH_SECONDS", 0.04), patch.object(tc, "DELIVERY_MARGIN_SECONDS", 0.01), patch.object(tc, "_http", side_effect=timed):
            self.assertEqual(len(list(model.embed(["x"] * 65))), 65)
        self.assertEqual(len(deadlines), 3)
        self.assertTrue(all(0.045 < value <= 0.05 for value in deadlines))
        hint = tc._client_session_hint()
        with tc.process_hold_guard(): importlib.reload(tc)
        self.assertEqual(hint, tc._client_session_hint())

    def test_capability_contract_cache_clamps_and_rejects(self):
        self.fake_ready()
        for schema in (1, 2):
            tc._capability_cache = None
            tc._pair, tc._cache_until, tc._backoff_until = None, 0, 0
            document = capabilities(schema_version=schema, limits={"max_items": 10000, "max_body_bytes": 2 << 20, "max_text_bytes": 65536})
            self.reply = lambda path, body: {"instance_id": INSTANCE, **document} if path == "/v1/capabilities" else None
            adapter = tc.select_embedder(tc.EMBEDDING_MODEL)
            self.assertIsNotNone(adapter)
            self.assertEqual(adapter._pair.capabilities["max_items"], 128)
            self.assertEqual(adapter._pair.capabilities["max_body_bytes"], 1 << 20)
            before = len([p for p, _ in self.requests if p == "/v1/capabilities"])
            tc._cache_until = 0
            self.assertIsNotNone(tc.select_embedder(tc.EMBEDDING_MODEL))
            self.assertEqual(len([p for p, _ in self.requests if p == "/v1/capabilities"]), before)
            tc._failed(tc._generation, "service_unavailable", INSTANCE)
            tc._backoff_until = 0
            self.assertIsNotNone(tc.select_embedder(tc.EMBEDDING_MODEL))
            self.assertEqual(len([p for p, _ in self.requests if p == "/v1/capabilities"]), before)
        missing = capabilities()
        del missing["limits"]["max_body_bytes"]
        for document in (capabilities(schema_version=3), capabilities(timeouts={"max_ms": 0}),
                         capabilities(timeouts={"max_ms": 1e12}), capabilities(timeouts={"max_ms": 1000.0}),
                         capabilities(limits={"max_items": 0, "max_body_bytes": 1048576, "max_text_bytes": 65536}),
                         capabilities(limits={"max_items": True, "max_body_bytes": 1048576, "max_text_bytes": 65536}),
                         capabilities(workloads={"supported": ["batch"]}), capabilities(client_session="yes"), missing):
            with self.subTest(document=document):
                tc._capability_cache = None
                tc._pair, tc._cache_until, tc._backoff_until = None, 0, 0
                self.reply = lambda path, body: {"instance_id": INSTANCE, **document} if path == "/v1/capabilities" else None
                self.assertIsNone(tc.select_embedder(tc.EMBEDDING_MODEL))
                self.assertEqual(tc.status_snapshot()["reason"], "capabilities_unsupported")
                self.assertEqual(tc.status_snapshot()["availability"]["state"], "incompatible")
        self.assertFalse(any(path.startswith("/v1/embeddings") for path, _ in self.requests))

    def test_workload_deadlines_exact_body_and_request_count(self):
        self.fake_ready()
        model = tc.select_embedder(tc.EMBEDDING_MODEL)
        list(model.embed(["raw"] * 65))
        model.embed_query("raw query")
        tc.select_reranker(tc.RERANKER_MODEL).rerank("raw", ["doc"] * 40)
        bodies = [body for _, body in self.requests if body is not None]
        self.assertEqual([len(body.get("input", body.get("documents"))) for body in bodies], [32, 32, 1, 1, 40])
        self.assertEqual([body["timeout_ms"] for body in bodies], [300000] * 3 + [30000] * 2)
        self.assertTrue(all("workload" in body for body in bodies))
        self.assertEqual([body["workload"] for body in bodies], ["batch"] * 3 + ["interactive"] * 2)
        self.assertTrue(all(body["include_timing"] is True for body in bodies))
        exact = len(tc._encoded({"model": "arctic-fp16-coreml", "timeout_ms": 300000,
                                "workload": "batch", "include_timing": True, "input": ["é"], "role": "document"}))
        model._pair.capabilities["max_body_bytes"] = exact + 1
        self.assertEqual(len(list(model.embed(["é"]))), 1)
        body = [body for _, body in self.requests if body is not None][-1]
        self.assertEqual(len(tc._encoded(body)), exact)

    def test_session_header_stable_optional_fork_and_safe_repr(self):
        captured = []
        def handler(request):
            captured.append(request.headers.get_all("Client-Session-Id"))
            body = request.rfile.read(0)
            payload = json.dumps({"instance_id": INSTANCE}).encode()
            request.send_response(200)
            request.send_header("Content-Type", "application/json")
            request.send_header("Content-Length", str(len(payload)))
            request.end_headers()
            request.wfile.write(payload)
        snapshot = self.serve(handler)
        for hint in (True, True, False):
            tc._http(snapshot, "/x", time.monotonic() + 1, b"{}", session_hint=hint)
        self.assertEqual(captured[0], captured[1])
        self.assertEqual(len(captured[0]), 1)
        self.assertRegex(captured[0][0], r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
        self.assertIsNone(captured[2])
        original = captured[0][0]
        self.assertNotIn(original, repr(tc._Pair(snapshot, *self.models)))
        self.assertNotIn(original, repr(tc.status_bundle_snapshot()))
        with patch.object(tc.os, "getpid", return_value=os.getpid() + 100):
            self.assertNotEqual(original, tc._client_session_hint())

    def test_timing_metadata_validation(self):
        self.fake_ready()
        model = tc.select_embedder(tc.EMBEDDING_MODEL)
        good = self.answer(None, "/v1/embeddings", 0, tc._encoded({"input": ["x"]}))
        good["metadata"] = {"workload": "interactive", "timing": {"queue_ms": 1, "execution_ms": 2, "total_ms": 3}}
        self.reply = lambda path, body: good
        model.embed_query("x")
        self.assertEqual(tc.status_snapshot()["timing"]["query_embedding"],
                         {"workload": "interactive", **good["metadata"]["timing"]})
        for field, value in (("workload", "batch"), ("queue_ms", "1"), ("execution_ms", -1), ("total_ms", float("nan"))):
            with self.subTest(field=field):
                mutated = copy.deepcopy(good)
                (mutated["metadata"] if field == "workload" else mutated["metadata"]["timing"])[field] = value
                self.reply = lambda path, body: mutated
                with self.assertRaises(tc.TensorwellUnavailable): model.embed_query("x")

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
                 {"WAVEFOUNDRY_EMBED_PROVIDER": "cuda"}]
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
        self.assertEqual([len(body["input"]) for body in bodies], [32, 32, 32, 32, 1])
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
        self.assertEqual(tc.status_snapshot()["reason"], "unexpected_response")
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
        def reload_during_models(snapshot, path, deadline, body=None, retry_budget=None, **kwargs):
            value = original_request(snapshot, path, deadline, body, retry_budget, **kwargs)
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
        def reload_during_inference(snapshot, path, deadline, body=None, retry_budget=None, **kwargs):
            value = original_request(snapshot, path, deadline, body, retry_budget, **kwargs)
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
