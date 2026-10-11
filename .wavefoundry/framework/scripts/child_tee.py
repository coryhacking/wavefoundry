"""Foreground upgrade children: continuously drained, contained diagnostic logs.

Only stdlib and the stdlib-only containment/isolation owners are used. Streams
remain separate; the labelled combined tail has best-effort arrival ordering.
"""
from __future__ import annotations

import codecs
from collections import deque
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
import uuid

import contained_files
import subprocess_util

LINE_CAP_CHARS = 4096
TAIL_LINES = 20
LOG_NAME_RETRIES = 8
RETAIN_RUNS = 5
_LOG_NAME = re.compile(r"upgrade-child-(\d{20}-[0-9a-f]{32})-([a-z0-9-]+)-(\d+)\.log\Z")
_ANSI = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07\x1b]*(?:\x07|\x1b\\))")
_RUNS: dict[str, str] = {}


def clean_output(text: str, token: str = "") -> str:
    """Redact both the raw and final canonical representation before any cap."""
    if token:
        text = text.replace(token, "[REDACTED]")
    text = _ANSI.sub("", text)
    text = "".join(c for c in text if c in "\n\t" or not (
        ord(c) < 32 or 127 <= ord(c) <= 159))
    return text.replace(token, "[REDACTED]") if token else text


def _run_id(root: Path) -> str:
    key = str(root.resolve())
    return _RUNS.setdefault(key, f"{time.time_ns():020d}-{uuid.uuid4().hex}")


def _prune(root: Path, current: str) -> None:
    """Delete only judged generated logs from older run groups, never links."""
    logs = root / ".wavefoundry/logs"
    fd = contained_files.open_contained_dir(root, (".wavefoundry", "logs"))
    try:
        names = os.listdir(fd if fd is not None else logs)
    finally:
        if fd is not None:
            os.close(fd)
    groups: dict[str, list[tuple[Path, tuple[int, int]]]] = {}
    for name in names:
        match = _LOG_NAME.fullmatch(name)
        if match is None:
            continue
        try:
            judged = contained_files.judge_contained_file(root, logs / name)
        except OSError:
            continue
        groups.setdefault(match[1], []).append(judged)
    keep = {current, *sorted((g for g in groups if g != current), reverse=True)[:RETAIN_RUNS - 1]}
    for group, entries in groups.items():
        if group in keep:
            continue
        for path, identity in entries:
            try:
                contained_files.unlink_contained(root, path, expected_identity=identity)
            except OSError:
                pass  # A concurrent replacement/locked file is never followed.


def _open_child_log(root: Path, phase: str):
    if re.fullmatch(r"[a-z0-9-]+", phase) is None:
        raise ValueError("child phase must be a generated literal label")
    run_id = _run_id(root)
    for suffix in range(LOG_NAME_RETRIES):
        path = root / ".wavefoundry/logs" / f"upgrade-child-{run_id}-{phase}-{suffix}.log"
        try:
            handle = contained_files.open_contained_append(root, path, exclusive=True)
        except (FileExistsError, PermissionError) as exc:
            # Containment refusals are not name collisions and must fail closed.
            if isinstance(exc, contained_files.ContainedFileRefused):
                raise
            if suffix + 1 == LOG_NAME_RETRIES:
                raise
        else:
            try:
                _prune(root, run_id)
            except BaseException:
                handle.close()
                raise
            return handle, path
    raise AssertionError("bounded name retry exhausted")


class _Lines:
    """Canonical stream assembly retains final-form token overlap before caps."""
    def __init__(self, token: str, emit):
        self.token, self.emit, self.pending = token, emit, ""
        self.escape, self.escape_chars = "", 0

    def _canonicalize(self, text: str) -> str:
        # Control sequences may straddle any pipe read or forced fragment.
        # Retain only parser state, never an unbounded unfinished OSC/CSI.
        value = []
        for char in text:
            if self.escape:
                self.escape_chars += 1
                if self.escape == "esc":
                    if char in "[]":
                        self.escape = "csi" if char == "[" else "osc"
                        continue
                    self.escape = ""
                    # A standalone ESC is removed; ordinary following text stays.
                elif self.escape == "csi":
                    if "@" <= char <= "~" or self.escape_chars >= LINE_CAP_CHARS:
                        self.escape = ""
                    continue
                elif self.escape == "osc":
                    if char == "\x07" or self.escape_chars >= LINE_CAP_CHARS:
                        self.escape = ""
                    elif char == "\x1b":
                        self.escape = "osc-esc"
                    continue
                else:  # OSC terminator ESC-backslash, possibly split at a read.
                    if char == "\\" or self.escape_chars >= LINE_CAP_CHARS:
                        self.escape = ""
                    else:
                        self.escape = "osc-esc" if char == "\x1b" else "osc"
                    continue
            if char == "\x1b":
                self.escape, self.escape_chars = "esc", 1
            elif char in "\n\t" or not (ord(char) < 32 or 127 <= ord(char) <= 159):
                value.append(char)
        return "".join(value)

    def feed(self, text: str, *, final: bool = False) -> None:
        self.pending += self._canonicalize(text)
        while self.pending:
            newline = self.pending.find("\n")
            if 0 <= newline < LINE_CAP_CHARS:
                cut = newline + 1
            elif len(self.pending) >= LINE_CAP_CHARS + len(self.token):
                cut = LINE_CAP_CHARS
                # If a token crosses the intended cut, emit before it and leave
                # the whole token assembled in the next bounded fragment.
                if self.token:
                    start = self.pending.rfind(self.token, 0, cut + len(self.token) - 1)
                    if 0 <= start < cut < start + len(self.token):
                        cut = start or start + len(self.token)
            elif final:
                cut = len(self.pending)
            else:
                break
            raw, self.pending = self.pending[:cut], self.pending[cut:]
            self.emit(clean_output(raw, self.token))


def _read_chunk(pipe, stopped):
    """Wait interruptibly for owned pipe bytes, including Windows Python 3.11."""
    fd = pipe.fileno()
    if os.name == "nt":
        import ctypes
        import msvcrt
        from ctypes import wintypes
        available = wintypes.DWORD()
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        peek = kernel.PeekNamedPipe
        peek.argtypes = (wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
                         ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD),
                         ctypes.POINTER(wintypes.DWORD))
        peek.restype = wintypes.BOOL
        while not stopped.is_set():
            if not peek(wintypes.HANDLE(msvcrt.get_osfhandle(fd)),
                        None, 0, None, ctypes.byref(available), None):
                error = ctypes.get_last_error()
                if error in (109, 232):  # Broken/closing pipe is ordinary EOF.
                    return b""
                raise ctypes.WinError(error)
            if available.value:
                return os.read(fd, min(4096, available.value))
            stopped.wait(0.05)
    else:
        import select
        while not stopped.is_set():
            if select.select([fd], [], [], 0.05)[0]:
                return os.read(fd, 4096)
    return b""


def run(cmd, *, root: Path, phase: str, cwd=None, env=None, timeout=None,
        check: bool = False, capture_output: bool = False, text: bool = True):
    """TEE a foreground child and return CompletedProcess with bounded ``tail``.

    ``capture_output`` preserves the existing pruning parser's captured stdout
    and stderr; other consumers retain only bounded tails in memory. Every
    write/forward sees assembled and scrubbed fragments, never raw pipe bytes.
    """
    root = Path(root)
    child_env = dict(os.environ if env is None else env)
    child_env["PYTHONUNBUFFERED"] = "1"
    token = str(child_env.get("WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN") or "")
    handle, log_path = _open_child_log(root, phase)
    streams = {"stdout": deque(maxlen=TAIL_LINES), "stderr": deque(maxlen=TAIL_LINES)}
    captured = {"stdout": [], "stderr": []}
    write_lock = threading.Lock()
    reader_errors: deque[str] = deque(maxlen=8)
    stopped = threading.Event()
    process = None
    sequence = 0

    def reader(pipe, label, target):
        decoder = codecs.getincrementaldecoder("utf-8")("replace")

        def emit(value):
            nonlocal sequence
            with write_lock:
                if stopped.is_set():
                    return
                bounded = value.rstrip("\n")[-LINE_CAP_CHARS:]
                sequence += 1
                streams[label].append((sequence, bounded))
                if capture_output:
                    captured[label].append(value)
                # A broken presentation destination must not stop draining the
                # pipe and deadlock its producer. Record the I/O failure.
                try:
                    handle.write(value)
                    handle.flush()
                except (OSError, ValueError) as exc:
                    reader_errors.append(type(exc).__name__)
            # A custom presentation sink may block. It never owns the file or
            # bookkeeping lock; arbitrary Python sinks cannot be interrupted.
            if target is not None and not stopped.is_set():
                try:
                    target.write(value)
                    target.flush()
                except (OSError, ValueError) as exc:
                    reader_errors.append(type(exc).__name__)

        lines = _Lines(token, emit)
        try:
            while True:
                chunk = _read_chunk(pipe, stopped)
                if not chunk:
                    break
                if stopped.is_set():
                    break
                lines.feed(decoder.decode(chunk))
            lines.feed(decoder.decode(b"", final=True), final=True)
        except BaseException as exc:
            reader_errors.append(type(exc).__name__)
        finally:
            pipe.close()

    try:
        process = subprocess_util.isolated_popen(
            cmd, cwd=cwd, env=child_env, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, start_new_session=False,
            creationflags=subprocess_util.no_window_creationflags(),
        )
        threads = [threading.Thread(target=reader, args=(pipe, label, target), daemon=True)
                   for pipe, label, target in [(process.stdout, "stdout", sys.stdout),
                                               (process.stderr, "stderr", sys.stderr)]]
        for thread in threads:
            thread.start()
        deadline = None if timeout is None else time.monotonic() + timeout
        try:
            returncode = process.wait(timeout=timeout)
            for thread in threads:
                thread.join(None if deadline is None else max(0.0, deadline - time.monotonic()))
            if any(thread.is_alive() for thread in threads):
                raise subprocess.TimeoutExpired(cmd, timeout)
        except BaseException:
            stopped.set()
            if process.poll() is None:
                process.kill()
            process.wait()
            for thread in threads:
                thread.join(0.2)
            raise
        result = subprocess.CompletedProcess(
            cmd, returncode,
            "".join(captured["stdout"]) if capture_output else "\n".join(value for _, value in streams["stdout"]),
            "".join(captured["stderr"]) if capture_output else "\n".join(value for _, value in streams["stderr"]),
        )
        retained = sorted((order, f"[{label}] {value}")
                          for label, lines in streams.items()
                          for order, value in list(lines)[-TAIL_LINES // 2:])
        result.tail = "\n".join(value for _, value in retained)
        result.log_path = str(log_path)
        result.log_errors = list(reader_errors)
        if check and returncode:
            raise subprocess.CalledProcessError(returncode, cmd, result.stdout, result.stderr)
        return result
    finally:
        with write_lock:
            stopped.set()
            handle.close()
