"""Bound offline rule processing in an owned, reusable Python child.

Only this module's private JSON protocol crosses the process boundary. Rule text
is data: neither provider actions nor arbitrary Python programs are accepted.
The caller must treat WorkerError as incomplete scanning, never a clean result.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
import tomllib
import weakref

if __name__ == "__main__" or sys.pycache_prefix is None:
    sys.dont_write_bytecode = True

_SCRIPTS_DIR = str(Path(__file__).resolve().parents[1])
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)
import bytecode_cache  # noqa: E402

if __name__ == "__main__":
    bytecode_cache.configure()

DETECTION_RELPATHS = tuple(".wavefoundry/framework/" + name for name in (
    "scan/cl100k_base.tiktoken.gz", "scan/words.txt.gz",
    "scan/manifest.json", "scan/NOTICE.md",
    "scripts/wave_lint_lib/expr_filter.py", "scripts/wave_lint_lib/secret_tokenizer.py",
    "scripts/wave_lint_lib/betterleaks_engine.py", "scripts/wave_lint_lib/betterleaks_worker.py",
    "scripts/wave_lint_lib/constants.py", "scripts/wave_lint_lib/secrets_validators.py",
))


def rules_fingerprint(root: Path, rule_paths=(".wavefoundry/framework/scan-rules.toml", "docs/scan-rules.toml")) -> str:
    """Shared cache/execution identity; imports remain in the reloaded package."""
    digest = hashlib.sha256()
    for rel in (*rule_paths, *DETECTION_RELPATHS):
        path = root / rel
        if path.exists():
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(65536), b""):
                    digest.update(chunk)
        digest.update(b"\x00")
    return digest.hexdigest()

MAX_REQUEST_BYTES = 32 * 1024 * 1024
MAX_RESPONSE_BYTES = 16 * 1024 * 1024
MAX_CONFIG_BYTES = 2 * 1024 * 1024
MAX_CONTENT_BYTES = 5 * 1024 * 1024
# Leave four seconds for bounded kill/drain cleanup inside the 120-second limit.
MAX_TIMEOUT_SECONDS = 115.0
_OPERATIONS = frozenset({"parse_toml", "configure", "path_excluded", "scan"})
_ERROR_CODES = frozenset({
    "worker_timeout", "worker_crashed", "worker_protocol", "worker_unavailable",
    "worker_closed", "worker_busy", "worker_input_too_large",
    "worker_response_too_large", "invalid_configuration", "invalid_operation",
    "worker_operation_failed",
})


class WorkerError(RuntimeError):
    """A path-free, content-free failure suitable for a scanner diagnostic."""

    def __init__(self, code: str):
        self.code = code if code in _ERROR_CODES else "worker_operation_failed"
        super().__init__(self.code)


def _validate_tree(value, *, byte_limit: int) -> None:
    """Reject excessive/unsupported JSON data without invoking custom encoders."""
    todo = [(value, 0)]
    nodes = strings = 0
    while todo:
        item, depth = todo.pop()
        nodes += 1
        if depth > 64 or nodes > 250_000:
            raise WorkerError("worker_input_too_large")
        kind = type(item)
        if kind is str:
            if len(item) > byte_limit:
                raise WorkerError("worker_input_too_large")
            strings += len(item.encode("utf-8", errors="surrogatepass"))
            if strings > byte_limit:
                raise WorkerError("worker_input_too_large")
        elif kind is dict:
            if nodes + len(todo) + 2 * len(item) > 250_000:
                raise WorkerError("worker_input_too_large")
            if any(type(key) is not str for key in item):
                raise WorkerError("worker_protocol")
            todo.extend((key, depth + 1) for key in item)
            todo.extend((child, depth + 1) for child in item.values())
        elif kind is list:
            if nodes + len(todo) + len(item) > 250_000:
                raise WorkerError("worker_input_too_large")
            todo.extend((child, depth + 1) for child in item)
        elif kind is float:
            if not math.isfinite(item):
                raise WorkerError("worker_protocol")
        elif kind not in (int, bool, type(None)):
            raise WorkerError("worker_protocol")


def _encode(value, limit: int) -> bytes:
    _validate_tree(value, byte_limit=limit)
    try:
        chunks, size = [], 1
        encoder = json.JSONEncoder(ensure_ascii=True, separators=(",", ":"), allow_nan=False)
        for chunk in encoder.iterencode(value):
            size += len(chunk)
            if size > limit:
                raise WorkerError("worker_input_too_large")
            chunks.append(chunk.encode("ascii"))
        raw = b"".join(chunks) + b"\n"
    except (ValueError, TypeError, RecursionError):
        raise WorkerError("worker_protocol") from None
    return raw


def _reject_constant(_value):
    raise ValueError("non-finite JSON number")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _decode(raw: bytes):
    try:
        return json.loads(raw, parse_constant=_reject_constant, object_pairs_hook=_unique_object)
    except (ValueError, UnicodeError, RecursionError):
        raise WorkerError("worker_protocol") from None


def _dispose(process: subprocess.Popen | None) -> None:
    if process is None:
        return
    try:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=2)
    except (OSError, subprocess.TimeoutExpired):
        pass
    for stream in (process.stdin, process.stdout, process.stderr):
        if stream is not None:
            try:
                stream.close()
            except OSError:
                pass


class _Client:
    """One serialized request owner; deadlines include startup and pipe I/O."""

    def __init__(self, command: list[str] | None = None):
        self._command = command or [sys.executable, "-B", str(Path(__file__).resolve()), "--worker"]
        self._owner = os.getpid()
        self._lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._process = None
        self._cancel = None
        self._closed = False
        self._sequence = 0
        self._execution_key = None

    def _start(self, cancel: threading.Event):
        scripts = str(Path(__file__).resolve().parents[1])
        if scripts not in sys.path:
            sys.path.insert(0, scripts)
        import subprocess_util
        process = subprocess_util.isolated_popen(
            self._command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, bufsize=0, close_fds=True,
        )
        with self._state_lock:
            if cancel.is_set() or self._closed:
                _dispose(process)
                raise WorkerError("worker_closed")
            self._process = process
        return process

    def _exchange(self, operation: str, payload: dict, timeout: float,
                  cancel: threading.Event, done: threading.Event, box: list) -> None:
        try:
            self._sequence += 1
            sequence = self._sequence
            request = _encode({"id": sequence, "op": operation, "payload": payload,
                               "budget": timeout}, MAX_REQUEST_BYTES)
            if cancel.is_set():
                raise WorkerError("worker_timeout")
            # The caller fingerprints engine code and assets as well as rules.
            # Reconstructing the engine in an existing interpreter would retain
            # old imported modules. A new execution identity needs a new child.
            if operation in {"configure", "path_excluded", "scan"}:
                execution_key = payload.get("cache_key", "")
                if type(execution_key) is str:
                    if self._execution_key is not None and execution_key != self._execution_key:
                        self._drop_process()
                    self._execution_key = execution_key
            process = self._process
            if process is None or process.poll() is not None:
                _dispose(process)
                process = self._start(cancel)
            view = memoryview(request)
            while view:
                written = process.stdin.write(view)
                if not written:
                    raise WorkerError("worker_crashed")
                view = view[written:]
            raw = process.stdout.readline(MAX_RESPONSE_BYTES + 1)
            if not raw:
                raise WorkerError("worker_crashed")
            if len(raw) > MAX_RESPONSE_BYTES:
                raise WorkerError("worker_response_too_large")
            if not raw.endswith(b"\n"):
                raise WorkerError("worker_protocol")
            response = _decode(raw)
            if (type(response) is not dict or response.get("id") != sequence
                    or type(response.get("id")) is not int
                    or type(response.get("ok")) is not bool):
                raise WorkerError("worker_protocol")
            _validate_tree(response, byte_limit=MAX_RESPONSE_BYTES)
            if response["ok"]:
                if set(response) != {"id", "ok", "result"} or type(response["result"]) is not dict:
                    raise WorkerError("worker_protocol")
                box.append(response["result"])
            else:
                if (set(response) != {"id", "ok", "error"}
                        or type(response["error"]) is not str or response["error"] not in _ERROR_CODES):
                    raise WorkerError("worker_protocol")
                raise WorkerError(response["error"])
        except WorkerError as exc:
            box.append(exc)
        except Exception:
            box.append(WorkerError("worker_unavailable"))
        finally:
            done.set()

    def request(self, operation: str, payload: dict, *, timeout: float = MAX_TIMEOUT_SECONDS) -> dict:
        if type(operation) is not str or operation not in _OPERATIONS or type(payload) is not dict:
            raise WorkerError("invalid_operation")
        if type(timeout) not in (int, float) or not 0 < timeout <= MAX_TIMEOUT_SECONDS or not math.isfinite(timeout):
            raise WorkerError("worker_protocol")
        deadline = time.monotonic() + timeout
        if not self._lock.acquire(timeout=timeout):
            raise WorkerError("worker_busy")
        thread = None
        try:
            if self._closed or os.getpid() != self._owner:
                raise WorkerError("worker_closed")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise WorkerError("worker_timeout")
            cancel, done, box = threading.Event(), threading.Event(), []
            with self._state_lock:
                self._cancel = cancel
            thread = threading.Thread(target=self._exchange,
                                      args=(operation, payload, remaining, cancel, done, box),
                                      daemon=True, name="offline-scan-io")
            thread.start()
            if not done.wait(max(0, deadline - time.monotonic())):
                cancel.set()
                self._drop_process()
                raise WorkerError("worker_timeout")
            if not box:
                self._drop_process()
                raise WorkerError("worker_protocol")
            if isinstance(box[0], WorkerError):
                self._drop_process()
                raise box[0]
            return box[0]
        except BaseException:
            with self._state_lock:
                if self._cancel is not None:
                    self._cancel.set()
            self._drop_process()
            if thread is not None:
                thread.join(timeout=2)
            raise
        finally:
            with self._state_lock:
                self._cancel = None
            self._lock.release()

    def _drop_process(self) -> None:
        with self._state_lock:
            process, self._process = self._process, None
        _dispose(process)

    def close(self) -> None:
        if self._owner != os.getpid():
            return  # A fork must never terminate its parent's owned process.
        with self._state_lock:
            self._closed = True
            if self._cancel is not None:
                self._cancel.set()
        self._drop_process()


_CLIENT = None
_CLIENT_LOCK = threading.Lock()


def worker_request(operation: str, payload: dict, *, timeout: float = MAX_TIMEOUT_SECONDS) -> dict:
    """Call the offline child; configure/scan cache_key identifies code and data.

    Callers using configure or scan must change cache_key when their execution
    inputs change. An omitted key is stable and offers no source-change check.
    """
    # Keep this module alive through an in-flight request. Once reload has
    # retired and collected it, a retained function must not start another child.
    owner = _MODULE_REFERENCE()
    if owner is None or not _MODULE_FINALIZER.alive:
        raise WorkerError("worker_closed")
    global _CLIENT
    with _CLIENT_LOCK:
        if _CLIENT is None or _CLIENT._owner != os.getpid():
            _CLIENT = _Client()
        client = _CLIENT
    return client.request(operation, payload, timeout=timeout)


def close_worker() -> None:
    global _CLIENT
    with _CLIENT_LOCK:
        client, _CLIENT = _CLIENT, None
    if client is not None:
        client.close()


# The callback keeps the globals dictionary, not the module object. It therefore
# closes a retired module's client when reload drops the module, and also runs
# at normal process exit. A plain atexit callback retained idle children until
# host exit even after the module itself had been collected.
_MODULE_REFERENCE = weakref.ref(sys.modules[__name__])
_MODULE_FINALIZER = weakref.finalize(sys.modules[__name__], close_worker)


def _offline_audit(event: str, _arguments) -> None:
    if (event.startswith("socket.") or event.startswith("subprocess.")
            or event.startswith("os.exec") or event.startswith("os.spawn")
            or event in {"os.system", "os.fork", "os.forkpty", "os.posix_spawn"}):
        raise PermissionError("offline scanner action denied")


def _alarm(seconds: float) -> None:
    # The parent enforces the deadline on every platform. POSIX additionally
    # bounds an orphaned regex that holds the GIL after its parent disappears.
    if hasattr(signal, "setitimer"):
        signal.signal(signal.SIGALRM, signal.SIG_DFL)
        signal.setitimer(signal.ITIMER_REAL, seconds)


class _Runtime:
    def __init__(self):
        self.key = None
        self.engine = None

    def execute(self, operation: str, payload: dict) -> dict:
        if operation == "parse_toml":
            text = payload.get("text")
            if type(text) is not str or len(text.encode("utf-8")) > MAX_CONFIG_BYTES:
                raise WorkerError("worker_input_too_large")
            try:
                result = tomllib.loads(text)
                _validate_tree(result, byte_limit=MAX_REQUEST_BYTES)
                return result
            except (ValueError, TypeError, RecursionError, WorkerError):
                raise WorkerError("invalid_configuration") from None
        if operation not in {"configure", "path_excluded", "scan"}:
            raise WorkerError("invalid_operation")
        config, cache_key = payload.get("config"), payload.get("cache_key", "")
        if type(config) is not dict or type(cache_key) is not str or len(cache_key) > 512:
            raise WorkerError("invalid_configuration")
        encoded = _encode(config, MAX_REQUEST_BYTES)
        identity = hashlib.sha256(encoded + cache_key.encode()).digest()
        if identity != self.key:
            from wave_lint_lib.betterleaks_engine import BetterleaksEngine
            self.engine, self.key = None, None
            try:
                candidate = BetterleaksEngine(config)
            except Exception:
                raise WorkerError("invalid_configuration") from None
            self.engine, self.key = candidate, identity
        if operation == "configure":
            return {"configured": True, "rule_count": len(config.get("rules", []))}
        if operation == "path_excluded":
            path = payload.get("path")
            if type(path) is not str or len(path) > 8192:
                raise WorkerError("worker_input_too_large")
            return {"excluded": self.engine.path_excluded(path)}
        content, path = payload.get("content"), payload.get("path")
        metadata_only = payload.get("metadata_only", False)
        if (type(content) is not str or type(path) is not str
                or type(metadata_only) is not bool or len(path) > 8192
                or len(content.encode("utf-8", errors="surrogatepass")) > MAX_CONTENT_BYTES):
            raise WorkerError("worker_input_too_large")
        result = self.engine.scan(content, path, metadata_only=metadata_only)
        if (type(result) is not dict or type(result.get("complete")) is not bool
                or type(result.get("findings")) is not list
                or type(result.get("diagnostics")) is not list):
            raise WorkerError("worker_protocol")
        return result


def _serve() -> int:
    scripts = str(Path(__file__).resolve().parents[1])
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    sys.addaudithook(_offline_audit)
    runtime = _Runtime()
    while True:
        _alarm(MAX_TIMEOUT_SECONDS)
        raw = sys.stdin.buffer.readline(MAX_REQUEST_BYTES + 1)
        if not raw:
            return 0
        if len(raw) > MAX_REQUEST_BYTES or not raw.endswith(b"\n"):
            return 2
        sequence = 0
        try:
            request = _decode(raw)
            if (type(request) is not dict or set(request) != {"id", "op", "payload", "budget"}
                    or type(request["id"]) is not int or request["id"] < 1
                    or type(request["op"]) is not str or request["op"] not in _OPERATIONS
                    or type(request["payload"]) is not dict
                    or type(request["budget"]) not in (int, float)
                    or not 0 < request["budget"] <= MAX_TIMEOUT_SECONDS):
                raise WorkerError("worker_protocol")
            sequence = request["id"]
            _alarm(request["budget"])
            _validate_tree(request, byte_limit=MAX_REQUEST_BYTES)
            result = runtime.execute(request["op"], request["payload"])
            response = {"id": sequence, "ok": True, "result": result}
            try:
                encoded = _encode(response, MAX_RESPONSE_BYTES)
            except WorkerError:
                raise WorkerError("worker_response_too_large") from None
        except WorkerError as exc:
            encoded = _encode({"id": sequence, "ok": False, "error": exc.code}, 1024)
        except Exception:
            encoded = _encode({"id": sequence, "ok": False, "error": "worker_operation_failed"}, 1024)
        sys.stdout.buffer.write(encoded)
        sys.stdout.buffer.flush()


if __name__ == "__main__":
    if sys.argv[1:] != ["--worker"]:
        raise SystemExit(2)
    raise SystemExit(_serve())
