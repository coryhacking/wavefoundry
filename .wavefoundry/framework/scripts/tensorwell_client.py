"""Optional, qualified Tensorwell inference; no daemon lifetime ownership.

Only these two artifact/runtime/preprocessing identities are admitted. They
were independently reconstructed from model-set-v3 and qualified against the
local full-class models (wave 20nju). No service-reported digest extends this
table. Discovery/selection never starts a service; only the MCP lifespan may
schedule the single bounded controller attempt.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import http.client
import json
import math
import os
from pathlib import Path
import platform
import re
import socket
import stat
import subprocess
import threading
import time
import weakref

EMBEDDING_MODEL = "Snowflake/snowflake-arctic-embed-s"
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
MODEL_SET_FINGERPRINT = "wf-model-set-2-20260811-arctic-s"
CANONICAL_MANIFEST_SHA256 = "22e19c0e4817d96f71882bd0c605a1bb9cbed8c957b2796ad92752d3e0250609"
EMBEDDING_IDENTITY = "sha256:5670c9e9f64e33744416fa5851a26656f42dd24e99e7dde0b106d00617b1c1c7"
RERANKER_IDENTITY = "sha256:3a14f1775368230d55eecc1fec7a144b17b845e5706bc47757cb45470df699f8"
# Cancellation qualification is for this controller, not a PID from discovery.
QUALIFIED_CONTROLLER_SHA256 = frozenset({
    "679dde180489a8fdb5f9e8e2302f70e0683c501e721d627e785cec671676cd92",
})
MAX_BODY_BYTES = 1 << 20
MAX_ITEM_BYTES = 64 << 10
MAX_ITEMS = 128
MAX_RESPONSE_BYTES = 2 << 20
DISCOVERY_SECONDS = 2.0
INFERENCE_SECONDS = 30.0
STARTUP_SECONDS = 30.0
CACHE_SECONDS = 5.0
BACKOFF_SECONDS = 5.0
CLI_OUTPUT_BYTES = 64 << 10
FLOAT32_MAX = float.fromhex("0x1.fffffep+127")


class TensorwellUnavailable(RuntimeError):
    """Safe failure: selected operations never silently retry another backend."""

    def __init__(self):
        super().__init__("Qualified Tensorwell inference is unavailable; retry the operation or use local inference.")


class _Race(Exception):
    pass


@dataclass(frozen=True)
class _Snapshot:
    port: int
    instance: str
    token: str = field(repr=False)


@dataclass(frozen=True)
class _Pair:
    snapshot: _Snapshot
    embedding: dict
    reranking: dict
    generation: int = 0


# In-place MCP reload refreshes code/pins while preserving process ownership.
# The reload helper holds process_hold_guard() and restores exception classes.
if "_lock" not in globals():
    _lock = threading.RLock()
if "_probe_lock" not in globals():
    _probe_lock = threading.Lock()
if "_startup_scheduled" not in globals():
    _startup_scheduled = False
if "_startup_worker" not in globals():
    _startup_worker = None
if "_status" not in globals():
    _status = {"backend": "local", "reason": "not_checked", "startup": "not_scheduled", "profiles": []}
if "_generation" not in globals():
    _generation = 0
else:
    _generation += 1
    _status.update(backend="local", reason="client_reloaded", profiles=[])
_pair: _Pair | None = None
_cache_until = 0.0
_backoff_until = 0.0

# Process-local diagnostics. Reload keeps weak ownership observations without
# keeping a model alive; absence after a reload is deliberately indeterminate.
_ROLES = ("query_embedding", "search_reranking", "memory_reranking")
_OWNER_SLOTS = ("docs_embedding", "code_embedding", "search_reranking", "memory_reranking")
if "_observation_started_at" not in globals():
    _observation_started_at = time.time()
if "_process_pid" not in globals():
    _process_pid = os.getpid()
if "_owners" not in globals():
    _owners = {slot: {"ref": None, "complete": _generation == 0, "model": None}
               for slot in _OWNER_SLOTS}
else:
    for _owner in _owners.values():
        _owner["complete"] = False
_sequence = 0
_roles = {role: {"selection": None, "last_attempt": None, "last_success": None}
          for role in _ROLES}
_availability = {"state": "not_checked" if _generation == 0 else "unknown",
                 "reason": "not_checked" if _generation == 0 else "client_reloaded",
                 "observed_at": None, "observed_monotonic": None}


def _observation_process() -> None:
    """Invalidate inherited telemetry on fork without changing provider routing."""
    global _process_pid, _observation_started_at, _sequence, _roles, _owners
    pid = os.getpid()
    if pid != _process_pid:
        _process_pid, _observation_started_at, _sequence = pid, time.time(), 0
        _roles = {role: {"selection": None, "last_attempt": None, "last_success": None} for role in _ROLES}
        _owners = {slot: {"ref": None, "complete": False, "model": None} for slot in _OWNER_SLOTS}
        _status.update(backend="local", reason="process_changed", profiles=[])
        _availability.update(state="unknown", reason="process_changed", observed_at=None, observed_monotonic=None)


def _observe_availability(state: str, reason: str) -> None:
    # Called only at the existing observation boundary, never by status reads.
    _observation_process()
    _availability.update(state=state, reason=reason, observed_at=time.time(),
                         observed_monotonic=time.monotonic())


def _provider(model) -> dict:
    # Read plain instance/class dictionaries, not arbitrary inference properties.
    try:
        attrs = vars(model)
    except TypeError:
        attrs = {}
    service = attrs.get("is_tensorwell", vars(type(model)).get("is_tensorwell")) is True
    accelerator = attrs.get("provider")
    if not isinstance(accelerator, str) or accelerator not in {"CPUExecutionProvider", "CoreMLExecutionProvider", "CUDAExecutionProvider",
                           "ROCMExecutionProvider", "DmlExecutionProvider"}:
        accelerator = "unknown"
    return {"provider": "tensorwell" if service else "in_process" if model is not None else None,
            "accelerator": "service_managed" if service else accelerator}


def observe_selection(role: str, model, reason: str) -> None:
    global _sequence
    with _lock:
        _observation_process()
        _sequence += 1
        _roles[role]["selection"] = {**_provider(model), "reason": reason,
                                    "at": time.time(), "sequence": _sequence, "epoch": _generation}


def attempt(role: str, model) -> tuple:
    global _sequence
    with _lock:
        _observation_process()
        _sequence += 1
        provenance = _provider(model)
        token = (role, _generation, _sequence, provenance, _process_pid)
        _roles[role]["last_attempt"] = {**provenance, "epoch": _generation,
            "sequence": _sequence, "started_at": time.time(), "completed_at": None,
            "provider_outcome": "running", "caller_outcome": "pending", "reason": None}
        return token


def provider_returned(token: tuple) -> None:
    role, epoch, sequence, _, pid = token
    with _lock:
        _observation_process()
        current = _roles[role]["last_attempt"]
        if epoch == _generation and pid == _process_pid and current is not None and current["sequence"] == sequence:
            current["provider_outcome"] = "returned"


def finish_attempt(token: tuple, *, returned: bool, accepted: bool, reason: str | None = None) -> None:
    role, epoch, sequence, start, pid = token
    with _lock:
        _observation_process()
        if epoch != _generation or pid != _process_pid:
            return
        current = _roles[role]["last_attempt"]
        # Latest-started attempt wins, independently of completion ordering.
        if current is not None and current["sequence"] == sequence:
            current.update(completed_at=time.time(), provider_outcome="returned" if returned else "failed",
                           caller_outcome="accepted" if accepted else "degraded", reason=reason)
        # A success from an older overlapping operation is still useful if no
        # newer-started accepted operation has been recorded. Its provenance is
        # carried in the token, rather than copied from the current attempt.
        success = _roles[role]["last_success"]
        if accepted and (success is None or sequence > success["sequence"]):
            # The caller keeps a bounded detached start record in its token.
            _roles[role]["last_success"] = {**start, "epoch": epoch, "sequence": sequence,
                                           "completed_at": time.time()}


def observe_owner(slot: str, model, model_name: str) -> None:
    with _lock:
        _observation_process()
        owner = _owners[slot]
        old = owner["ref"]() if owner["ref"] is not None else None
        if old is not None and old is not model:
            owner["complete"] = False
        try:
            owner["ref"] = weakref.ref(model)
        except TypeError:
            owner["ref"] = None
            owner["complete"] = False
        owner["model"] = (model_name if model_name in {EMBEDDING_MODEL, RERANKER_MODEL} else "other")


def ownership_unknown(slot: str) -> None:
    """Construction may create sessions before a cache takes ownership."""
    with _lock:
        _observation_process()
        _owners[slot]["complete"] = False


def inference_status_snapshot() -> dict:
    """Detached fixed-size observations; no model, filesystem or service work."""
    with _lock:
        _observation_process()
        models = {}
        identities = {}
        live = {slot: owner["ref"]() if owner["ref"] is not None else None
                for slot, owner in _owners.items()}
        for slot, owner in _owners.items():
            model = live[slot]
            identities[slot] = id(model) if model is not None else None
            models[slot] = {"state": "loaded" if model is not None else
                           "not_loaded" if owner["complete"] else "unknown",
                           "model": owner["model"], "ownership_complete": owner["complete"]}
        for slot, entry in models.items():
            entry["shared_with"] = [other for other in _OWNER_SLOTS if other != slot
                                    and identities[slot] is not None and identities[slot] == identities[other]]
        return {"scope": {"pid": _process_pid, "observation_started_at": _observation_started_at,
                          "epoch": _generation, "other_processes": "not_observed"},
                "roles": {role: {key: dict(value) if value is not None else None
                                  for key, value in record.items()} for role, record in _roles.items()},
                "local_models": models}


def process_hold_guard():
    """Serialize reload with short state transitions, never discovery I/O."""
    return _lock


def _reason(reason: str) -> None:
    with _lock:
        _status.update(backend="local", reason=reason, profiles=[])
        state = ("policy_disabled" if reason in {"disabled", "unsupported_host", "provider_policy"}
                 else "incompatible" if reason == "incompatible_profiles" else "unavailable")
        _observe_availability(state, reason)


def status_snapshot() -> dict:
    """Cached, nonsecret diagnostics only: no discovery, HTTP or CLI calls."""
    with _lock:
        _observation_process()
        observed = _availability["observed_monotonic"]
        availability = {key: value for key, value in _availability.items() if key != "observed_monotonic"}
        availability["stale"] = observed is None or time.monotonic() - observed >= CACHE_SECONDS
        availability["detail"] = ("Both pinned models were compatible at the last readiness/descriptor check."
                                  if availability["reason"] == "qualified_pair" else
                                  "Last process-local observation; status does not check the service.")
        return {**_status, "profiles": list(_status["profiles"]), "availability": availability}


def status_bundle_snapshot() -> dict:
    """Keep availability and inference in the same process/reload snapshot."""
    with _lock:
        return {"tensorwell": status_snapshot(), "inference": inference_status_snapshot()}


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _policy_reason() -> str | None:
    if _truthy("WAVEFOUNDRY_DISABLE_TENSORWELL"):
        return "disabled"
    if platform.system() != "Darwin" or platform.machine().lower() not in {"arm64", "aarch64"}:
        return "unsupported_host"
    requested = os.environ.get("WAVEFOUNDRY_EMBED_PROVIDER", "auto").strip().lower()
    if requested not in {"", "auto", "coreml"}:
        return "provider_policy"
    selected = os.environ.get("WAVEFOUNDRY_EMBED_PROVIDER_SELECTED", "")
    if requested in {"", "auto"} and selected and selected != "CoreMLExecutionProvider":
        return "provider_policy"
    return None


def _json(data: bytes):
    def pairs(items):
        obj = {}
        for key, value in items:
            if key in obj:
                raise ValueError("duplicate field")
            obj[key] = value
        return obj
    return json.loads(data, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite")))


def _remaining(deadline: float) -> float:
    left = deadline - time.monotonic()
    if left <= 0:
        raise TimeoutError
    return left


def _private_file(directory: int, name: str, limit: int) -> bytes:
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077 or info.st_size > limit):
            raise ValueError("unsafe discovery")
        data = os.read(fd, limit + 1)
        if len(data) > limit:
            raise ValueError("large discovery")
        return data
    finally:
        os.close(fd)


def _discovery(deadline: float) -> _Snapshot:
    _remaining(deadline)
    directory = os.open(Path.home() / ".tensorwell", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        info = os.fstat(directory)
        if info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError("unsafe discovery")
        # endpoint-token-endpoint; one additional observation for rotation.
        for _ in range(2):
            _remaining(deadline)
            first = _private_file(directory, "endpoint.json", 4096)
            token = _private_file(directory, "token", 64)
            second = _private_file(directory, "endpoint.json", 4096)
            if first != second:
                continue
            endpoint = _json(first)
            if not isinstance(endpoint, dict) or set(endpoint) - {"url", "pid", "instance_id", "api_version", "launch_id"}:
                raise ValueError("invalid discovery")
            url = endpoint.get("url")
            match = re.fullmatch(r"http://127\.0\.0\.1:([1-9][0-9]{0,4})", url or "")
            if not match or not 0 < int(match[1]) <= 65535:
                raise ValueError("nonloopback discovery")
            instance = endpoint.get("instance_id")
            if (endpoint.get("api_version") != "v1" or not isinstance(instance, str)
                    or re.fullmatch(r"[0-9a-f]{64}", instance) is None
                    or type(endpoint.get("pid")) is not int or endpoint["pid"] <= 0
                    or (endpoint.get("launch_id") is not None and
                        re.fullmatch(r"[0-9a-f]{64}", endpoint["launch_id"]) is None)
                    or re.fullmatch(rb"[0-9a-f]{64}", token) is None):
                raise ValueError("invalid discovery")
            return _Snapshot(int(match[1]), instance, token.decode("ascii"))
        raise _Race
    finally:
        os.close(directory)


def _http(snapshot: _Snapshot, path: str, deadline: float, body: bytes | None = None) -> dict:
    """Direct literal-loopback HTTP; never consult proxies or follow redirects.

    A socket watchdog enforces the total deadline, including headers and a
    slowly dribbling response. Inactivity timeouts alone do not provide that.
    """
    connection = http.client.HTTPConnection("127.0.0.1", snapshot.port, timeout=_remaining(deadline))
    owned_socket = []
    def expire():
        if owned_socket:
            try:
                owned_socket[0].shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
    timer = threading.Timer(_remaining(deadline), expire)
    timer.daemon = True
    timer.start()
    response = None
    try:
        connection.connect()
        # HTTP/1.0 / Connection: close can detach and close connection.sock
        # while HTTPResponse still owns its file. Retain a duplicate solely
        # for the watchdog's shutdown of that same underlying connection.
        owned_socket.append(connection.sock.dup())
        connection.sock.settimeout(_remaining(deadline))
        headers = {"Authorization": "Bearer " + snapshot.token, "Accept": "application/json"}
        if body is not None:
            if len(body) > MAX_BODY_BYTES:
                raise ValueError("large request")
            headers["Content-Type"] = "application/json"
        connection.request("POST" if body is not None else "GET", path, body=body, headers=headers)
        response = connection.getresponse()
        if response.status == 401:
            raise _Race
        if response.status != 200 or response.getheader("Content-Type", "").split(";")[0].strip().lower() != "application/json":
            raise ValueError("unavailable response")
        size = response.getheader("Content-Length")
        if size is not None and (not size.isdecimal() or int(size) > MAX_RESPONSE_BYTES):
            raise ValueError("large response")
        chunks = bytearray()
        while True:
            owned_socket[0].settimeout(_remaining(deadline))
            part = response.read1(min(65536, MAX_RESPONSE_BYTES + 1 - len(chunks)))
            if not part:
                break
            chunks.extend(part)
            if len(chunks) > MAX_RESPONSE_BYTES:
                raise ValueError("large response")
        _remaining(deadline)
        value = _json(bytes(chunks))
        if not isinstance(value, dict) or value.get("instance_id") != snapshot.instance:
            raise ValueError("changed instance")
        return value
    finally:
        timer.cancel()
        if response is not None:
            response.close()
        connection.close()
        if owned_socket:
            owned_socket[0].close()


def _request(snapshot: _Snapshot, path: str, deadline: float, body: bytes | None = None,
             retry_budget: list[int] | None = None) -> dict:
    try:
        return _http(snapshot, path, deadline, body)
    except (_Race, ConnectionError, OSError, http.client.HTTPException):
        # At most one rediscovery, and never switch instance for this operation.
        if retry_budget is not None:
            if retry_budget[0] == 0:
                raise ValueError("rediscovery exhausted") from None
            retry_budget[0] -= 1
        refreshed = _discovery(deadline)
        if refreshed.instance != snapshot.instance:
            raise ValueError("changed instance")
        return _http(refreshed, path, deadline, body)


def _descriptor(value, task: str) -> bool:
    if not isinstance(value, dict):
        return False
    embedding = task == "embedding"
    return (value.get("id") == ("arctic-fp16-coreml" if embedding else "minilm-fp16-coreml")
            and value.get("identity") == (EMBEDDING_IDENTITY if embedding else RERANKER_IDENTITY)
            and value.get("task") == task and value.get("precision") == "fp16"
            and value.get("requested_provider") == "CoreMLExecutionProvider"
            and value.get("registered_provider") == "CoreMLExecutionProvider"
            and (type(value.get("dimensions")) is int and value["dimensions"] == 384
                 if embedding else value.get("dimensions") is None))


def _selection_result(value, reason: str, diagnostic: dict | None):
    # Owned by this invocation, never read back from process-global status.
    if diagnostic is not None:
        diagnostic["reason"] = reason
    return value


def _qualified_pair(total_deadline: float | None = None, *, diagnostic: dict | None = None) -> _Pair | None:
    global _pair, _cache_until, _backoff_until
    policy = _policy_reason()
    if policy:
        _reason(policy)
        return _selection_result(None, policy, diagnostic)
    # Separate serialization from the status lock: status_snapshot never waits
    # for disk/HTTP discovery running in another thread.
    deadline = time.monotonic() + DISCOVERY_SECONDS
    if total_deadline is not None:
        deadline = min(deadline, total_deadline)
    if not _probe_lock.acquire(timeout=max(0, deadline - time.monotonic())):
        return _selection_result(None, "discovery_contended", diagnostic)
    try:
        now = time.monotonic()
        generation = _generation
        if now < _backoff_until:
            return _selection_result(None, "discovery_backoff", diagnostic)
        if _pair is not None and now < _cache_until:
            return _selection_result(_pair, "qualified_pair", diagnostic)
        try:
            # Model-set mappings are code pins, not facts learned from HTTP.
            import model_bundle
            if model_bundle.EMBEDDING_COMPATIBILITY_FINGERPRINT != MODEL_SET_FINGERPRINT:
                raise ValueError("model set changed")
            snapshot = _discovery(deadline)
            retry_budget = [1]
            health = _request(snapshot, "/health/ready", deadline, retry_budget=retry_budget)
            if health.get("status") != "ready":
                raise ValueError("not ready")
            descriptors = _request(snapshot, "/v1/models", deadline, retry_budget=retry_budget).get("data")
            if not isinstance(descriptors, list) or len(descriptors) > 5:
                raise ValueError("invalid models")
            embedding = [d for d in descriptors if _descriptor(d, "embedding")]
            reranking = [d for d in descriptors if _descriptor(d, "reranking")]
            if len(embedding) != 1 or len(reranking) != 1:
                with _lock:
                    if generation == _generation:
                        _reason("incompatible_profiles")
                        _pair = None
                        _backoff_until = now + BACKOFF_SECONDS
                        return _selection_result(None, "incompatible_profiles", diagnostic)
                    return _selection_result(None, "client_reloaded", diagnostic)
            with _lock:
                if generation != _generation:
                    return _selection_result(None, "client_reloaded", diagnostic)
                _pair = _Pair(snapshot, embedding[0], reranking[0], generation)
                _cache_until = time.monotonic() + CACHE_SECONDS
                _status.update(backend="tensorwell", reason="qualified_pair", profiles=[embedding[0]["id"], reranking[0]["id"]])
                _observe_availability("ready_compatible", "qualified_pair")
                return _selection_result(_pair, "qualified_pair", diagnostic)
        except Exception:
            with _lock:
                if generation == _generation:
                    _pair = None
                    _backoff_until = time.monotonic() + BACKOFF_SECONDS
                    _reason("discovery_unavailable")
                    return _selection_result(None, "discovery_unavailable", diagnostic)
                return _selection_result(None, "client_reloaded", diagnostic)
    finally:
        _probe_lock.release()


def _failed(generation: int | None = None) -> None:
    global _pair, _cache_until, _backoff_until
    with _lock:
        if generation is not None and generation != _generation:
            return
        _pair = None
        _cache_until = 0
        _backoff_until = time.monotonic() + BACKOFF_SECONDS
        _reason("inference_unavailable")


def _text(value) -> None:
    if not isinstance(value, str) or len(value.encode("utf-8")) > MAX_ITEM_BYTES:
        raise ValueError("invalid input")


def _encoded(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


class _Adapter:
    is_tensorwell = True
    provider = "Tensorwell/CoreMLExecutionProvider"
    batch_size = 32
    def __init__(self, pair: _Pair, model_name: str, task: str):
        self._pair = pair
        self.model_name = model_name
        self._task = task
        self._model = pair.embedding if task == "embedding" else pair.reranking
        if task == "reranking":
            self.batch_size = 40

    def _operation(self, texts, role="document", query=None):
        try:
            deadline = time.monotonic() + INFERENCE_SECONDS
            retry_budget = [1]
            if self._pair.generation != _generation:
                raise ValueError("client reloaded")
            if _policy_reason() or (self._task == "reranking" and _truthy("WAVEFOUNDRY_DISABLE_RERANKER")):
                raise ValueError("disabled")
            values = list(texts)
            for text in values:
                _text(text)
            encoded_sizes = [len(_encoded(text)) for text in values]
            if query is not None:
                _text(query)
            output = []
            offset = 0
            # Send empty arrays explicitly, preserving the service contract.
            while offset < len(values) or (not values and offset == 0):
                items = []
                def payload(batch):
                    base = {"model": self._model["id"], "timeout_ms": max(1, min(30000, int(_remaining(deadline) * 1000)))}
                    if self._task == "embedding":
                        return {**base, "input": batch, "role": role}
                    return {**base, "query": query, "documents": batch}
                # Exact UTF-8 JSON scalar sizes, commas and the empty-array
                # envelope, with five reserved timeout digits. Serialize the
                # complete body only once rather than every growing prefix.
                used = len(_encoded(payload([]))) + 5
                for index in range(offset, min(len(values), offset + MAX_ITEMS)):
                    extra = encoded_sizes[index] + (1 if items else 0)
                    if used + extra > MAX_BODY_BYTES:
                        break
                    items.append(values[index])
                    used += extra
                if values and not items:
                    raise ValueError("large request")
                body = _encoded(payload(items))
                response = _request(self._pair.snapshot,
                                    "/v1/embeddings" if self._task == "embedding" else "/v1/rerank",
                                    deadline, body, retry_budget)
                if not _descriptor(response.get("model"), self._task):
                    raise ValueError("changed model")
                data = response.get("data")
                if not isinstance(data, list) or len(data) != len(items):
                    raise ValueError("invalid count")
                for i, row in enumerate(data):
                    if not isinstance(row, dict) or type(row.get("index")) is not int or row["index"] != i:
                        raise ValueError("invalid order")
                    value = row.get("embedding") if self._task == "embedding" else row.get("score")
                    numbers = value if self._task == "embedding" else [value]
                    if (not isinstance(numbers, list) or (self._task == "embedding" and len(numbers) != 384)
                            or any(type(n) not in (int, float) or not math.isfinite(n)
                                   or abs(n) > FLOAT32_MAX for n in numbers)):
                        raise ValueError("invalid output")
                    output.append(value)
                offset += len(items)
                if not values:
                    break
            if self._pair.generation != _generation:
                raise ValueError("client reloaded")
            return output
        except Exception:
            _failed(self._pair.generation)
            raise TensorwellUnavailable() from None

    def embed(self, texts, batch_size=256, **kwargs):
        # Eager completion prevents yielding unpublished partial service output.
        return iter(self._operation(texts))

    def embed_query(self, text: str):
        return self._operation([text], role="query")[0]

    def rerank(self, query: str, texts):
        return self._operation(texts, query=query)


def select_embedder(model_name: str, precision_class: str = "full", *, diagnostic: dict | None = None):
    if model_name != EMBEDDING_MODEL:
        return _selection_result(None, "unsupported_model", diagnostic)
    if precision_class != "full":
        return _selection_result(None, "index_precision_mismatch", diagnostic)
    pair = _qualified_pair(diagnostic=diagnostic)
    return _Adapter(pair, model_name, "embedding") if pair is not None else None


def select_reranker(model_name: str, *, diagnostic: dict | None = None):
    if model_name != RERANKER_MODEL:
        return _selection_result(None, "unsupported_model", diagnostic)
    if _truthy("WAVEFOUNDRY_DISABLE_RERANKER"):
        return _selection_result(None, "reranker_disabled", diagnostic)
    pair = _qualified_pair(diagnostic=diagnostic)
    return _Adapter(pair, model_name, "reranking") if pair is not None else None


def _controller(root: Path) -> Path | None:
    """Controlled PATH lookup: exclude CWD/repository, including resolved links."""
    excluded = (root.resolve(), Path.cwd().resolve())
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if not entry or not Path(entry).is_absolute():
            continue
        candidate = Path(entry) / "tensorwell"
        try:
            directory = Path(entry).resolve()
            resolved = candidate.resolve(strict=True)
            if any(directory == p or directory.is_relative_to(p) or resolved.is_relative_to(p) for p in excluded):
                continue
            if resolved.is_file() and os.access(resolved, os.X_OK):
                return resolved
        except OSError:
            continue
    return None


def _controller_file_identity(executable: Path) -> tuple:
    info = executable.stat(follow_symlinks=False)
    if not stat.S_ISREG(info.st_mode):
        raise ValueError("unsafe controller")
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _cli(executable: Path, args: list[str], deadline: float, expected_identity: tuple | None = None) -> dict:
    """Bounded capture; terminate/reap only the exact owned controller child.

    Drainers cap retained bytes while continuing to drain, so an untrusted
    read-only status command cannot exhaust memory or block on a full pipe.
    No process-group/session creation and no generic tree-kill helper.
    """
    _remaining(deadline)
    if expected_identity is not None and _controller_file_identity(executable) != expected_identity:
        raise ValueError("changed controller")
    import subprocess_util
    child = subprocess.Popen([str(executable), *args], stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             creationflags=subprocess_util.no_window_creationflags())
    captured = [bytearray(), bytearray()]
    overflow = threading.Event()
    def drain(stream, index):
        try:
            while True:
                part = stream.read(4096)
                if not part:
                    break
                available = CLI_OUTPUT_BYTES - len(captured[index])
                captured[index].extend(part[:available])
                if len(part) > available:
                    overflow.set()
        finally:
            stream.close()
    readers = [threading.Thread(target=drain, args=(stream, i), daemon=True)
               for i, stream in enumerate((child.stdout, child.stderr))]
    for reader in readers:
        reader.start()
    try:
        # Reserve cancellation/reaping time within the same total budget.
        child.wait(timeout=max(0.001, _remaining(deadline) - 1.0))
    except (subprocess.TimeoutExpired, TimeoutError):
        child.kill()
        child.wait(timeout=_remaining(deadline))
        raise TimeoutError from None
    finally:
        for reader in readers:
            reader.join(timeout=max(0, min(0.1, deadline - time.monotonic())))
    _remaining(deadline)
    if any(reader.is_alive() for reader in readers) or overflow.is_set() or child.returncode != 0:
        raise ValueError("controller unavailable")
    value = _json(bytes(captured[0]))
    if not isinstance(value, dict):
        raise ValueError("controller unavailable")
    return value


def _controller_digest(executable: Path, deadline: float) -> str:
    """Hash bounded regular bytes once; refuse links and concurrent replacement."""
    fd = os.open(executable, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > 64 << 20:
            raise ValueError("unsafe controller")
        digest = hashlib.sha256()
        remaining = (64 << 20) + 1
        while True:
            _remaining(deadline)
            block = os.read(fd, min(65536, remaining))
            if not block:
                break
            remaining -= len(block)
            if remaining <= 0:
                raise ValueError("large controller")
            digest.update(block)
        after = os.fstat(fd)
        current = executable.stat(follow_symlinks=False)
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if identity(before) != identity(after) or identity(after) != identity(current):
            raise ValueError("changed controller")
        _remaining(deadline)
        return digest.hexdigest()
    finally:
        os.close(fd)


def _startup(root: Path) -> None:
    deadline = time.monotonic() + STARTUP_SECONDS
    try:
        if _qualified_pair(deadline) is not None:
            with _lock:
                _status["startup"] = "reused"
            return
        executable = _controller(root)
        if executable is None:
            _reason("controller_absent")
            return
        # Unknown controllers are never executed automatically. HTTP ready
        # reuse above needs no controller and remains available.
        executable_identity = _controller_file_identity(executable)
        if _controller_digest(executable, deadline) not in QUALIFIED_CONTROLLER_SHA256:
            _reason("controller_unqualified")
            return
        report = _cli(executable, ["status", "--json"], deadline, executable_identity)
        state = report.get("status")
        if state == "stopped":
            result = _cli(executable, ["start", "--json", "--no-menu"], deadline, executable_identity)
            if (result.get("schema_version") != 1 or result.get("outcome") not in {"started", "reused"}
                    or result.get("code") is not None):
                _reason("startup_failed")
                return
            state = "ready"
        if state not in {"ready", "starting"}:
            _reason("service_unavailable")
            return
        # Starting is observed only; eventual readiness never triggers a second start.
        while _remaining(deadline) > 1.0:
            global _backoff_until
            with _lock:
                _backoff_until = 0
            if _qualified_pair(deadline) is not None:
                with _lock:
                    _status["startup"] = "ready"
                return
            if state == "ready":
                return
            time.sleep(min(0.2, _remaining(deadline)))
        raise TimeoutError
    except TimeoutError:
        _reason("startup_timeout")
    except Exception:
        _reason("startup_unavailable")
    finally:
        with _lock:
            if _status["startup"] == "scheduled":
                _status["startup"] = "finished"


def start_background(root: Path) -> None:
    """Called by actual serving lifespan, never imports/build/status/reload.

    No shutdown action: the shared daemon always remains operator-owned.
    """
    global _startup_scheduled, _startup_worker
    with _lock:
        if _startup_scheduled:
            return
        _startup_scheduled = True
        reason = _policy_reason()
        if reason:
            _reason(reason)
            _status["startup"] = "skipped"
            return
        _status["startup"] = "scheduled"
        thread = threading.Thread(target=_startup, args=(Path(root),),
                                  daemon=True, name="wavefoundry-tensorwell-start")
        _startup_worker = thread
        thread.start()
