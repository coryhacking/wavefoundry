"""Optional, qualified Tensorwell inference; no daemon lifetime ownership.

Only these two artifact/runtime/preprocessing identities are admitted. They
were independently reconstructed from model-set-v3 and qualified against the
local full-class models (wave 20nju). No service-reported digest extends this
table. Discovery/selection never starts a service; only the MCP lifespan may
schedule the single bounded controller attempt.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import http.client
import json
import math
import os
from pathlib import Path
import platform
import re
import random
import socket
import stat
import subprocess
import threading
import time
import weakref
import uuid

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
BATCH_SECONDS = 300.0
DELIVERY_MARGIN_SECONDS = 10.0
BATCH_ITEMS = 32
MAX_ATTEMPTS = 4
OVERLOAD_FLOOR_SECONDS = 1.0
OVERLOAD_CEILING_SECONDS = 60.0
OVERLOAD_JITTER_SECONDS = 1.0
DEADLINE_BACKOFF_SECONDS = 2.0
UNAVAILABLE_BACKOFF_SECONDS = (1.0, 2.0)
INTERACTIVE_LIMIT = 4
STATS_SECONDS = 1.0
_OUTCOMES = frozenset({"overloaded", "deadline_exceeded", "service_unavailable", "transport_uncertain",
                       "invalid_request", "unauthorized", "model_not_found", "request_timeout",
                       "payload_rejected", "unexpected_response"})
_HTTP_REASONS = {429: "overloaded", 504: "deadline_exceeded", 503: "service_unavailable", 400: "invalid_request",
                 401: "unauthorized", 404: "model_not_found", 408: "request_timeout", 413: "payload_rejected", 415: "payload_rejected"}
_DESELECT = frozenset({"transport_uncertain", "service_unavailable", "unauthorized", "unexpected_response"})
STARTUP_SECONDS = 30.0
CACHE_SECONDS = 5.0
BACKOFF_SECONDS = 5.0
CLI_OUTPUT_BYTES = 64 << 10
FLOAT32_MAX = float.fromhex("0x1.fffffep+127")

_embedding_request_observer = ContextVar("embedding_request_observer", default=None)


@contextmanager
def observe_embedding_requests():
    """Observe only logical embedding requests in this consuming call context.

    Not daemon counters or a lifetime snapshot; retries stay inside _request.
    """
    counts = {"offered": 0, "succeeded": 0}
    token = _embedding_request_observer.set(counts)
    try:
        yield counts
    finally:
        _embedding_request_observer.reset(token)


class TensorwellUnavailable(RuntimeError):
    """Safe failure: selected operations never silently retry another backend."""

    def __init__(self, reason="unexpected_response", *, status=None, code=None, phase="request"):
        reason = reason if reason in _OUTCOMES else "unexpected_response"
        self.reason = reason
        self.diagnostic = {"reason": reason, "status": status, "code": code, "phase": phase}
        super().__init__("Qualified Tensorwell inference is unavailable; retry the operation or use local inference. " + reason)


class _HTTPFailure(ValueError):
    def __init__(self, status, code=None, retryable=None, retry_after=None, *, reason=None):
        self.status = status
        self.code = code if isinstance(code, str) and re.fullmatch(r"[a-z_]{1,40}", code) and code in _OUTCOMES else None
        self.reason = reason if reason in _OUTCOMES else self.code or _HTTP_REASONS.get(status, "unexpected_response")
        self.retryable, self.retry_after = retryable, retry_after
        super().__init__("Unavailable HTTP response: " + self.reason)


class _CapabilitiesUnsupported(ValueError):
    def __init__(self, *, status=None, code=None):
        # Retain bounded protocol facts only; never the source exception.
        self.status = status if type(status) is int and 100 <= status <= 599 else None
        self.code = code if isinstance(code, str) and re.fullmatch(r"[a-z_]{1,40}", code) and code in _OUTCOMES else None
        super().__init__("Unsupported Tensorwell capabilities")


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
    capabilities: dict = field(default_factory=dict)


# In-place MCP reload refreshes code/pins while preserving process ownership.
# The reload helper holds process_hold_guard() and restores exception classes.
if "_lock" not in globals():
    _lock = threading.RLock()
if "_probe_lock" not in globals():
    _probe_lock = threading.Lock()
if "_batch_lock" not in globals():
    _batch_lock = threading.Lock()
    _interactive_slots = threading.BoundedSemaphore(INTERACTIVE_LIMIT)
    _attempt_context = threading.local()
if "_counters" not in globals():
    _counters = {name: 0 for name in ("offered", "succeeded", "overloaded", "deadline_exceeded", "unavailable",
                                    "transport_uncertain", "rejected", "cancelled")}
_last_readiness_at = None
_stats = None
_stats_reason = "absent"
_stats_until = 0.0
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
_capability_cache: tuple[str, dict] | None = None
_cache_until = 0.0
_backoff_until = 0.0

# Process-local diagnostics. Reload keeps weak ownership observations without
# keeping a model alive; absence after a reload is deliberately indeterminate.
_ROLES = ("query_embedding", "search_reranking", "memory_reranking")
_OWNER_SLOTS = ("docs_embedding", "code_embedding", "search_reranking", "memory_reranking")
if "_observation_started_at" not in globals():
    _observation_started_at = time.time()
if "_session_hint" not in globals():
    _session_hint = None
    _session_pid = None
_timing = {}
_timing_sequence = {}

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
    global _timing, _timing_sequence, _counters, _last_readiness_at, _stats, _stats_reason, _stats_until
    pid = os.getpid()
    if pid != _process_pid:
        _process_pid, _observation_started_at, _sequence = pid, time.time(), 0
        _timing, _timing_sequence = {}, {}
        _counters = dict.fromkeys(_counters, 0)
        _last_readiness_at, _stats, _stats_reason, _stats_until = None, None, "absent", 0.0
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
    label = attrs.get("provider_label")
    declared_service = (attrs.get("is_service_provider", vars(type(model)).get("is_service_provider")) is True
                        and isinstance(label, str) and re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", label) is not None)
    accelerator = attrs.get("provider")
    if not isinstance(accelerator, str) or accelerator not in {"CPUExecutionProvider", "CoreMLExecutionProvider", "CUDAExecutionProvider",
                           "ROCMExecutionProvider", "DmlExecutionProvider"}:
        accelerator = "unknown"
    return {"provider": label if declared_service else "tensorwell" if service else "in_process" if model is not None else None,
            "accelerator": "service_managed" if service or declared_service else accelerator}


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
        _attempt_context.token = token
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
            if current.get("reason") in _OUTCOMES and not accepted:
                reason = current["reason"]
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
        if getattr(_attempt_context, "token", None) == token:
            del _attempt_context.token


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
                 else "incompatible" if reason in {"incompatible_profiles", "capabilities_unsupported"} else "unavailable")
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
        return {**_status, "profiles": list(_status["profiles"]), "availability": availability,
                "capabilities": dict(_pair.capabilities, session_hint_in_use=bool(
                    _pair.capabilities.get("client_session_hint") and _session_pid == os.getpid() and _session_hint))
                    if _pair is not None and _status["backend"] == "tensorwell" else None,
                "timing": {role: dict(value) for role, value in _timing.items()},
                "counters": dict(_counters), "last_readiness_at": _last_readiness_at,
                "stats": json.loads(json.dumps(_stats)) if _stats is not None else None,
                "stats_reason": _stats_reason}


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
    # The automatic setup decision applies only to local ONNX execution.
    # A CPU fallback for one uncovered model must not veto a qualified service
    # for another model. Explicit operator policy above remains authoritative.
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


def _http(snapshot: _Snapshot, path: str, deadline: float, body: bytes | None = None,
          *, session_hint: bool = False) -> dict:
    """Direct literal-loopback HTTP; never consult proxies or follow redirects.

    A socket watchdog enforces the total deadline, including headers and a
    slowly dribbling response. Inactivity timeouts alone do not provide that.
    """
    connection = http.client.HTTPConnection("127.0.0.1", snapshot.port, timeout=min(DISCOVERY_SECONDS, _remaining(deadline)) if body is not None else _remaining(deadline))
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
            if session_hint:
                headers["Client-Session-Id"] = _client_session_hint()
        connection.request("POST" if body is not None else "GET", path, body=body, headers=headers)
        response = connection.getresponse()
        is_json = response.getheader("Content-Type", "").split(";")[0].strip().lower() == "application/json"
        if not is_json and response.status == 200:
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
        if response.status != 200:
            code = retryable = value = None
            try:
                value = _json(bytes(chunks)) if is_json else None
                error = value.get("error") if isinstance(value, dict) else None
                if isinstance(error, dict) and type(error.get("retryable")) is bool:
                    code, retryable = error.get("code"), error["retryable"]
            except (ValueError, UnicodeError):
                pass
            if isinstance(value, dict) and "instance_id" in value and value["instance_id"] != snapshot.instance:
                raise _HTTPFailure(response.status, reason="unexpected_response")
            raise _HTTPFailure(response.status, code, retryable, response.getheader("Retry-After"))
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
             retry_budget: list[int] | None = None, *, session_hint: bool = False,
             workload: str | None = None, operation_deadline: float | None = None,
             service_seconds: float | None = None) -> dict:
    # Discovery retains its one consistent rediscovery, inference has one
    # non-overlapping retry loop bounded by the enclosing operation deadline.
    inference = body is not None
    operation_deadline = operation_deadline if operation_deadline is not None else deadline
    retry_budget = retry_budget if retry_budget is not None else [1]
    transport_retried = deadline_retried = False
    unavailable_retries = 0
    if inference:
        with _lock:
            _counters["offered"] += 1
        observer = _embedding_request_observer.get()
        if path == "/v1/embeddings" and observer is not None:
            observer["offered"] += 1
    for number in range(MAX_ATTEMPTS):
        try:
            if inference and service_seconds is not None:
                deadline = min(operation_deadline, time.monotonic() + service_seconds + DELIVERY_MARGIN_SECONDS)
            result = _http(snapshot, path, deadline, body, session_hint=session_hint)
            _remaining(deadline)
            return result
        except (_Race, ConnectionError, OSError, http.client.HTTPException, _HTTPFailure) as failure:
            reason = (failure.reason if isinstance(failure, _HTTPFailure) else
                      "unauthorized" if isinstance(failure, _Race) else "transport_uncertain")
            if number + 1 >= MAX_ATTEMPTS:
                raise _request_failure(reason, failure) from None
            if reason in {"transport_uncertain", "unauthorized"}:
                if retry_budget[0] <= 0 or (reason == "transport_uncertain" and transport_retried):
                    if not inference:
                        raise ValueError("rediscovery exhausted") from None
                    raise _request_failure(reason, failure) from None
                retry_budget[0] -= 1
                transport_retried |= reason == "transport_uncertain"
                try:
                    refreshed = _discovery(min(operation_deadline, time.monotonic() + DISCOVERY_SECONDS))
                    if refreshed.instance != snapshot.instance:
                        raise ValueError("changed instance")
                    snapshot = refreshed
                except Exception:
                    if not inference:
                        raise ValueError("changed instance") from None
                    raise _request_failure(reason, failure) from None
                continue
            if not inference:
                raise
            if reason == "overloaded":
                remaining = operation_deadline - time.monotonic()
                if remaining < OVERLOAD_FLOOR_SECONDS:
                    raise _request_failure(reason, failure) from None
                raw = failure.retry_after if isinstance(failure, _HTTPFailure) else None
                # Bound parsing work; huge decimals are simply above the ceiling.
                seconds = (int(raw) if len(raw) < 10 else OVERLOAD_CEILING_SECONDS) if isinstance(raw, str) and raw.isascii() and raw.isdecimal() else OVERLOAD_FLOOR_SECONDS
                delay = max(OVERLOAD_FLOOR_SECONDS, min(seconds, OVERLOAD_CEILING_SECONDS, remaining))
                delay += random.random() * OVERLOAD_JITTER_SECONDS
            elif reason == "deadline_exceeded" and workload == "batch" and not deadline_retried:
                deadline_retried = True
                delay = DEADLINE_BACKOFF_SECONDS
            elif reason == "service_unavailable" and unavailable_retries < len(UNAVAILABLE_BACKOFF_SECONDS):
                delay = UNAVAILABLE_BACKOFF_SECONDS[unavailable_retries]
                unavailable_retries += 1
            else:
                raise _request_failure(reason, failure) from None
            if not _retry_wait(delay, operation_deadline):
                raise _request_failure(reason, failure) from None
            if reason == "service_unavailable":
                while True:
                    try:
                        health = _http(snapshot, "/health/ready", min(operation_deadline, time.monotonic() + DISCOVERY_SECONDS))
                        if health.get("status") != "ready":
                            raise ValueError("not ready")
                        _readiness_observed()
                        break
                    except Exception:
                        if unavailable_retries >= len(UNAVAILABLE_BACKOFF_SECONDS):
                            raise _request_failure(reason, failure) from None
                        delay = UNAVAILABLE_BACKOFF_SECONDS[unavailable_retries]
                        unavailable_retries += 1
                        if not _retry_wait(delay, operation_deadline):
                            raise _request_failure(reason, failure) from None
    raise TensorwellUnavailable("unexpected_response")


def _request_failure(reason: str, failure) -> TensorwellUnavailable:
    return TensorwellUnavailable(reason, status=getattr(failure, "status", None), code=getattr(failure, "code", None))


def _retry_wait(seconds: float, deadline: float) -> bool:
    if seconds < 0 or seconds >= deadline - time.monotonic():
        return False
    time.sleep(seconds)
    return time.monotonic() < deadline


def _readiness_observed() -> None:
    global _last_readiness_at
    with _lock:
        _last_readiness_at = time.time()


def _client_session_hint() -> str:
    global _session_hint, _session_pid
    with _lock:
        pid = os.getpid()
        if _session_hint is None or _session_pid != pid:
            _session_hint, _session_pid = str(uuid.uuid4()), pid
        return _session_hint


def _capabilities(value) -> dict:
    if not isinstance(value, dict) or type(value.get("schema_version")) is not int or value["schema_version"] not in {1, 2}:
        raise _CapabilitiesUnsupported
    schema = value["schema_version"]
    for key in ("limits", "timeouts", "workloads", "timing"):
        if not isinstance(value.get(key), dict):
            raise _CapabilitiesUnsupported
    result = {"schema": schema}
    for key, container, wire_key, maximum in (
            ("max_timeout_ms", "timeouts", "max_ms", int(BATCH_SECONDS * 1000)),
            ("max_items", "limits", "max_items", MAX_ITEMS),
            ("max_body_bytes", "limits", "max_body_bytes", MAX_BODY_BYTES),
            ("max_input_bytes", "limits", "max_text_bytes", MAX_ITEM_BYTES)):
        number = value[container].get(wire_key)
        if type(number) is not int or number <= 0 or (key == "max_timeout_ms" and not 1000 <= number <= 300000):
            raise _CapabilitiesUnsupported
        result[key] = min(number, maximum)
    workloads = value["workloads"].get("supported")
    if (not isinstance(workloads, list) or len(workloads) > 8 or
            any(not isinstance(item, str) for item in workloads) or not {"interactive", "batch"} <= set(workloads)):
        raise _CapabilitiesUnsupported
    timing = value["timing"]
    if (timing.get("request_flag") != "include_timing" or timing.get("unit") != "milliseconds"
            or timing.get("rounding") != "floor"):
        raise _CapabilitiesUnsupported
    if schema == 2:
        session = value.get("client_session")
        if (not isinstance(session, dict) or session.get("header") != "Client-Session-Id"
                or session.get("format") != "uuid-shaped-ascii-8-4-4-4-12-hex"
                or session.get("optional") is not True or session.get("authentication") is not False):
            raise _CapabilitiesUnsupported
    result["client_session_hint"] = schema == 2
    return result


def _response_timing(value, workload: str, role: str, token=None) -> None:
    if "metadata" not in value:
        return
    metadata = value["metadata"]
    if not isinstance(metadata, dict) or metadata.get("workload") != workload:
        raise ValueError("invalid timing")
    timing = metadata.get("timing")
    if not isinstance(timing, dict):
        raise ValueError("invalid timing")
    result = {"workload": workload}
    for key in ("queue_ms", "execution_ms", "total_ms"):
        number = timing.get(key)
        if type(number) is not int or not 0 <= number < (1 << 31):
            raise ValueError("invalid timing")
        result[key] = number
    with _lock:
        if token is None or (token[1] == _generation and token[2] >= _timing_sequence.get(role, -1)):
            _timing[role] = result
            if token is not None:
                _timing_sequence[role] = token[2]


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


def _selection_result(value, reason: str, diagnostic: dict | None, *, phase=None, status=None, code=None):
    # Owned by this invocation, never read back from process-global status.
    if diagnostic is not None:
        diagnostic["reason"] = reason
        if phase in {"discovery", "capabilities", "readiness"}:
            diagnostic["phase"] = phase
            if type(status) is int and 100 <= status <= 599:
                diagnostic["status"] = status
            if isinstance(code, str) and re.fullmatch(r"[a-z_]{1,40}", code) and code in _OUTCOMES:
                diagnostic["code"] = code
    return value


def _qualified_pair(total_deadline: float | None = None, *, diagnostic: dict | None = None) -> _Pair | None:
    global _pair, _cache_until, _backoff_until, _capability_cache
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
        phase = "discovery"
        try:
            # Model-set mappings are code pins, not facts learned from HTTP.
            import model_bundle
            if model_bundle.EMBEDDING_COMPATIBILITY_FINGERPRINT != MODEL_SET_FINGERPRINT:
                raise ValueError("model set changed")
            snapshot = _discovery(deadline)
            retry_budget = [1]
            phase = "capabilities"
            if _capability_cache is not None and _capability_cache[0] == snapshot.instance:
                capabilities = _capability_cache[1]
            else:
                try:
                    capabilities = _capabilities(_request(snapshot, "/v1/capabilities", deadline, retry_budget=retry_budget))
                    if generation == _generation:
                        _capability_cache = (snapshot.instance, capabilities)
                except Exception as failure:
                    if generation == _generation:
                        _capability_cache = None
                    metadata = failure if isinstance(failure, (_HTTPFailure, _CapabilitiesUnsupported)) else None
                    raise _CapabilitiesUnsupported(status=metadata.status if metadata is not None else None,
                                                   code=metadata.code if metadata is not None else None) from None
            phase = "readiness"
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
                        return _selection_result(None, "incompatible_profiles", diagnostic, phase=phase)
                    return _selection_result(None, "client_reloaded", diagnostic)
            with _lock:
                if generation != _generation:
                    return _selection_result(None, "client_reloaded", diagnostic)
                _pair = _Pair(snapshot, embedding[0], reranking[0], generation, capabilities)
                _cache_until = time.monotonic() + CACHE_SECONDS
                _status.update(backend="tensorwell", reason="qualified_pair", profiles=[embedding[0]["id"], reranking[0]["id"]])
                _observe_availability("ready_compatible", "qualified_pair")
                _readiness_observed()
                qualified = _pair
            _refresh_stats(qualified)
            return _selection_result(qualified, "qualified_pair", diagnostic)
        except Exception as failure:
            with _lock:
                if generation == _generation:
                    _pair = None
                    _backoff_until = time.monotonic() + BACKOFF_SECONDS
                    reason = "capabilities_unsupported" if isinstance(failure, _CapabilitiesUnsupported) else "discovery_unavailable"
                    _reason(reason)
                    metadata = failure if isinstance(failure, (_HTTPFailure, _CapabilitiesUnsupported)) else None
                    return _selection_result(None, reason, diagnostic, phase=phase,
                                             status=metadata.status if metadata is not None else None,
                                             code=metadata.code if metadata is not None else None)
                return _selection_result(None, "client_reloaded", diagnostic)
    finally:
        _probe_lock.release()


def _refresh_stats(pair: _Pair) -> None:
    """Best-effort cache refresh outside status and interactive admission."""
    global _stats, _stats_reason, _stats_until
    if time.monotonic() < _stats_until:
        return
    result, reason = None, "invalid"
    try:
        value = _http(pair.snapshot, "/v1/stats", time.monotonic() + STATS_SECONDS)
        if type(value.get("schema_version")) is not int or value["schema_version"] not in {2, 3}:
            raise ValueError("invalid stats")
        rows = value.get("models")
        if not isinstance(rows, list):
            raise ValueError("invalid stats")
        profiles = {pair.embedding["id"], pair.reranking["id"]}
        models = {}
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("model"), dict) or not isinstance(row["model"].get("id"), str):
                raise ValueError("invalid stats")
            profile = row["model"]["id"]
            if profile not in profiles:
                continue
            if profile in models:
                raise ValueError("duplicate stats model")
            models[profile] = row
        result = {"schema_version": value["schema_version"], "models": {}}
        numeric = {"configured_sessions", "resident_sessions", "ready_sessions", "active_sessions",
                   "known_clients_active", "known_clients_queued", "unknown_active_requests", "unknown_queued_requests", "load_count"}
        labels = {"optional_state", "suppression_reason"}
        for profile in (pair.embedding["id"], pair.reranking["id"]):
            source = models.get(profile)
            if not isinstance(source, dict):
                raise ValueError("invalid stats")
            safe = {}
            for key in numeric | labels:
                container = source["model"] if key == "load_count" else source
                if key not in container:
                    continue
                value = container[key]
                if key in labels and value is None:
                    continue
                if key in numeric:
                    if type(value) is not int or not 0 <= value < (1 << 53):
                        raise ValueError("invalid stats")
                elif not isinstance(value, str) or re.fullmatch(r"[a-z0-9_-]{1,64}", value) is None:
                    raise ValueError("invalid stats")
                safe[key] = value
            result["models"][profile] = safe
        reason = None
    except _HTTPFailure as failure:
        reason = "absent" if failure.status == 404 else "invalid"
        result = None
    except Exception:
        result = None
    with _lock:
        if pair.generation == _generation and _pair is not None and _pair.snapshot.instance == pair.snapshot.instance:
            _stats, _stats_reason = result, reason
            _stats_until = time.monotonic() + CACHE_SECONDS


def _failed(generation: int | None = None, reason="unexpected_response", instance: str | None = None) -> None:
    global _pair, _cache_until, _backoff_until
    with _lock:
        if generation is not None and generation != _generation:
            return
        if instance is not None and _pair is not None and _pair.snapshot.instance != instance:
            return
        _pair = None
        _cache_until = 0
        _backoff_until = time.monotonic() + BACKOFF_SECONDS
        _reason(reason)


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

    def _operation(self, texts, role="document", query=None, *, workload="batch"):
        token = getattr(_attempt_context, "token", None)
        observation_role = token[0] if token is not None and token[1] == _generation else "query_embedding" if role == "query" else "search_reranking" if query is not None else "docs_embedding"
        slot = None
        started = time.monotonic()
        try:
            retry_budget = [1]
            if self._pair.generation != _generation:
                raise ValueError("client reloaded")
            if _policy_reason() or (self._task == "reranking" and _truthy("WAVEFOUNDRY_DISABLE_RERANKER")):
                raise ValueError("disabled")
            values = list(texts)
            caps = self._pair.capabilities
            service_seconds = min(BATCH_SECONDS, caps["max_timeout_ms"] / 1000) if workload == "batch" else min(INFERENCE_SECONDS, caps["max_timeout_ms"] / 1000)
            timeout_ms = int(service_seconds * 1000)
            item_limit = min(caps["max_items"], BATCH_ITEMS if workload == "batch" else MAX_ITEMS)
            for text in values:
                _text(text)
                if len(text.encode("utf-8")) > caps["max_input_bytes"]:
                    raise ValueError("invalid input")
            encoded_sizes = [len(_encoded(text)) for text in values]
            if query is not None:
                _text(query)
                if len(query.encode("utf-8")) > caps["max_input_bytes"]:
                    raise ValueError("invalid input")
            output = []
            offset = 0
            batches = []
            # Send empty arrays explicitly, preserving the service contract.
            while offset < len(values) or (not values and offset == 0):
                items = []
                def payload(batch):
                    base = {"model": self._model["id"], "timeout_ms": timeout_ms, "workload": workload, "include_timing": True}
                    if self._task == "embedding":
                        return {**base, "input": batch, "role": role}
                    return {**base, "query": query, "documents": batch}
                # Size the final constant envelope exactly.
                used = len(_encoded(payload([])))
                for index in range(offset, min(len(values), offset + item_limit)):
                    extra = encoded_sizes[index] + (1 if items else 0)
                    if used + extra > caps["max_body_bytes"]:
                        break
                    items.append(values[index])
                    used += extra
                if values and not items:
                    raise ValueError("large request")
                body = _encoded(payload(items))
                if len(body) > caps["max_body_bytes"]:
                    raise ValueError("large request")
                batches.append((body, len(items)))
                offset += len(items)
                if not values:
                    break
            operation_deadline = started + (len(batches) if workload == "batch" else 1) * (service_seconds + DELIVERY_MARGIN_SECONDS)
            if workload == "batch":
                if not _batch_lock.acquire(timeout=max(0, operation_deadline - time.monotonic())):
                    raise TensorwellUnavailable("overloaded")
                slot = _batch_lock
            for body, count in batches:
                deadline = min(operation_deadline, time.monotonic() + service_seconds + DELIVERY_MARGIN_SECONDS)
                if workload == "interactive":
                    if not _interactive_slots.acquire(timeout=max(0, deadline - time.monotonic())):
                        with _lock:
                            _counters["offered"] += 1
                        raise TensorwellUnavailable("overloaded")
                    slot = _interactive_slots
                response = _request(self._pair.snapshot,
                                    "/v1/embeddings" if self._task == "embedding" else "/v1/rerank",
                                    deadline, body, retry_budget, session_hint=caps["client_session_hint"], workload=workload,
                                    operation_deadline=operation_deadline, service_seconds=service_seconds)
                _remaining(operation_deadline)
                if not _descriptor(response.get("model"), self._task):
                    raise ValueError("changed model")
                data = response.get("data")
                if not isinstance(data, list) or len(data) != count:
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
                _response_timing(response, workload, observation_role, token)
                with _lock:
                    # Validation and lock admission consume the same operation budget.
                    try:
                        _remaining(operation_deadline)
                    except TimeoutError:
                        raise TensorwellUnavailable("deadline_exceeded", phase="response_validation") from None
                    _counters["succeeded"] += 1
                    observer = _embedding_request_observer.get()
                    if self._task == "embedding" and observer is not None:
                        observer["succeeded"] += 1
                    if self._pair.generation == _generation and _pair is not None and _pair.snapshot.instance == self._pair.snapshot.instance:
                        _status["reason"] = "qualified_pair"
                if workload == "interactive":
                    slot.release()
                    slot = None
            if self._pair.generation != _generation:
                raise ValueError("client reloaded")
            return output
        except BaseException as failure:
            cancelled = not isinstance(failure, Exception)
            error = failure if isinstance(failure, TensorwellUnavailable) else TensorwellUnavailable(
                "invalid_request" if isinstance(failure, ValueError) and str(failure) in {"invalid input", "large request"} else
                "transport_uncertain" if isinstance(failure, (TimeoutError, OSError)) else "unexpected_response",
                phase="response_validation" if isinstance(failure, ValueError) else "request")
            reason = error.reason
            with _lock:
                if self._pair.generation == _generation:
                    if _pair is None or _pair.snapshot.instance == self._pair.snapshot.instance:
                        if reason in _DESELECT:
                            _failed(self._pair.generation, reason, self._pair.snapshot.instance)
                        else:
                            _status["reason"] = reason
                    counter = "cancelled" if cancelled else reason if reason in {"overloaded", "deadline_exceeded", "transport_uncertain"} else "unavailable" if reason in {"service_unavailable", "unauthorized", "unexpected_response"} else "rejected"
                    _counters[counter] += 1
                    if token is not None:
                        current = _roles[token[0]]["last_attempt"]
                        if token[1] == _generation and current is not None and current["sequence"] == token[2]:
                            current["reason"] = reason
            if cancelled:
                raise
            raise error from None
        finally:
            if slot is not None:
                slot.release()

    def embed(self, texts, batch_size=256, **kwargs):
        # Eager completion prevents yielding unpublished partial service output.
        return iter(self._operation(texts))

    def embed_query(self, text: str):
        return self._operation([text], role="query", workload="interactive")[0]

    def rerank(self, query: str, texts):
        return self._operation(texts, query=query, workload="interactive")


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
    """Controlled PATH lookup: exclude the target repository, including resolved links."""
    excluded = (root.resolve(),)
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
        # Handle and path stats may disagree on ctime alone (Windows,
        # Python 3.12; change 21bzm), so the cross-kind check omits it.
        if identity(before) != identity(after) or identity(after)[:4] != identity(current)[:4]:
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
