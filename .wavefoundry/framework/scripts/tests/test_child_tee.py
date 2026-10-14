"""Upgrade diagnostic streaming uses real inert children in owned temp roots."""
from __future__ import annotations

import contextlib
import io
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import child_tee
import contained_files as cf


class StreamingOpenTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.path = self.root / ".wavefoundry/logs/test.log"

    def test_regular_append_truncate_exclusive_and_mode(self):
        with cf.open_contained_append(self.root, self.path) as h:
            h.write("before\n")
        with cf.open_contained_append(self.root, self.path) as h:
            h.write("after\n")
        self.assertEqual(self.path.read_text(), "before\nafter\n")
        if os.name != "nt":
            self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)
        with self.assertRaises(FileExistsError):
            cf.open_contained_append(self.root, self.path, exclusive=True)
        self.assertEqual(self.path.read_text(), "before\nafter\n")
        with cf.open_contained_append(self.root, self.path, truncate=True) as h:
            h.write("fresh\n")
        self.assertEqual(self.path.read_text(), "fresh\n")

    @unittest.skipIf(os.name == "nt", "POSIX symlink and FIFO creation")
    def test_lexical_parent_target_fifo_and_runtime_alias_refused_before_truncate(self):
        self.path.parent.mkdir(parents=True)
        target = self.root / "target"
        target.write_text("untouched")
        self.path.symlink_to(target)
        with self.assertRaises(cf.ContainedFileRefused):
            cf.open_contained_append(self.root, self.path, truncate=True)
        self.assertEqual(target.read_text(), "untouched")
        self.path.unlink()
        self.path.parent.rename(self.path.parent.with_name("inside"))
        self.path.parent.symlink_to(self.path.parent.with_name("inside"), target_is_directory=True)
        with self.assertRaises(cf.ContainedFileRefused):
            cf.open_contained_append(self.root, self.path)
        self.path.parent.unlink()
        self.path.parent.mkdir()
        os.mkfifo(self.path)
        with self.assertRaises(cf.ContainedFileRefused):
            cf.open_contained_append(self.root, self.path, truncate=True)
        self.path.unlink()
        lock = self.root / ".wavefoundry/live.lock"
        lock.write_text("lock")
        os.link(lock, self.path)
        with self.assertRaises(cf.ContainedFileRefused):
            cf.open_contained_append(self.root, self.path, truncate=True)
        self.assertEqual(lock.read_text(), "lock")

    def test_path_branch_reparse_before_and_after_open(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("untouched")
        for late in (False, True):
            opened = False
            def seam(stage):
                nonlocal opened
                if stage == "append_open":
                    opened = True
            with self.subTest(late=late), patch.object(cf, "_dir_fd_supported", return_value=False), \
                    patch.object(cf, "_checkpoint", side_effect=seam), \
                    patch.object(cf, "_is_windows_link", side_effect=lambda p: p == str(self.path) and (opened or not late)):
                with self.assertRaises(cf.ContainedFileRefused):
                    cf.open_contained_append(self.root, self.path, truncate=True)
            self.assertEqual(self.path.read_text(), "untouched")


class ChildTeeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.out, self.err = io.StringIO(), io.StringIO()

    def run_child(self, source, **kwargs):
        with contextlib.redirect_stdout(self.out), contextlib.redirect_stderr(self.err):
            return child_tee.run([sys.executable, "-c", source], root=self.root,
                                 phase="fixture", cwd=str(self.root), **kwargs)

    def test_both_pipes_drain_and_failure_tail_is_labelled_bounded(self):
        result = self.run_child("import sys\nfor i in range(80):\n print('x'*5000)\n print('y'*5000,file=sys.stderr)\nprint('stdout reason')\nprint('stderr reason',file=sys.stderr)\nsys.exit(7)", timeout=10)
        self.assertEqual(result.returncode, 7)
        self.assertIn("[stdout] stdout reason", result.tail)
        self.assertIn("[stderr] stderr reason", result.tail)
        self.assertLessEqual(len(result.tail.splitlines()), child_tee.TAIL_LINES)
        self.assertTrue(all(len(line) <= child_tee.LINE_CAP_CHARS + 10 for line in result.tail.splitlines()))
        content = Path(result.log_path).read_text()
        self.assertIn("stdout reason", content)
        self.assertIn("stderr reason", content)

    def test_capture_byte_boundaries_preserve_small_text_and_utf8_final_tail(self):
        cap = 1024 * 1024
        for size in (cap - 1, cap, cap + 1, cap * 3):
            for chunk_size in (4093, 8192):
                with self.subTest(size=size, chunk_size=chunk_size):
                    count = size - len(b"HEAD\nFINAL\n")
                    value = "HEAD\n" + "\u00e9" * (count // 2) + "x" * (count % 2) + "FINAL\n"
                    captured = child_tee._BoundedCapture()
                    for start in range(0, len(value), chunk_size):
                        captured.write(value[start:start + chunk_size])
                        self.assertLessEqual(len(captured.head) + len(captured.tail), cap)
                    result = captured.getvalue()
                    self.assertLessEqual(len(result.encode("utf-8")), cap)
                    self.assertEqual(captured.truncated, size > cap)
                    self.assertTrue(result.startswith("HEAD\n"))
                    self.assertTrue(result.endswith("FINAL\n"))
                    if size <= cap:
                        self.assertEqual(result, value)
                    else:
                        self.assertIn("child capture output elided", result)

    def test_capture_caps_each_stream_after_scrubbing_and_continues_forwarding(self):
        token = "fixture-private-token"
        source = ("import sys; print('HEAD-OUT'); print('HEAD-ERR',file=sys.stderr); "
                  "exec(\"for i in range(300):\\n print('é'*4096)\\n print('🙂'*4096,file=sys.stderr)\"); "
                  f"print('\\x1b[31m{token}\\x1b[0m'); "
                  f"print({token!r},file=sys.stderr); "
                  "print('FINAL-OUT'); print('FINAL-ERR',file=sys.stderr); sys.exit(7)")
        result = self.run_child(source, capture_output=True, timeout=20,
                                env={**os.environ, "WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN": token})
        self.assertEqual(result.returncode, 7)
        self.assertEqual(result.capture_truncated, {"stdout": True, "stderr": True})
        for label, output, forwarded in (("OUT", result.stdout, self.out.getvalue()),
                                          ("ERR", result.stderr, self.err.getvalue())):
            self.assertLessEqual(len(output.encode("utf-8")), 1024 * 1024)
            self.assertGreater(len(forwarded.encode("utf-8")), 1024 * 1024)
            self.assertTrue(output.startswith("HEAD-" + label))
            self.assertTrue(output.endswith("FINAL-" + label + "\n"))
            self.assertIn("[REDACTED]", output)
            self.assertNotIn(token, output + forwarded)
            self.assertNotIn("\x1b", output + forwarded)
        self.assertEqual(result.log_errors, [])
        self.assertLessEqual(Path(result.log_path).stat().st_size, 1024 * 1024)

    def test_unflushed_output_is_live_before_exit_and_only_env_addition(self):
        seen = threading.Event()
        class Sink(io.StringIO):
            def write(self, text):
                if "unflushed" in text:
                    seen.set()
                return super().write(text)
        output = Sink()
        actual = child_tee.subprocess_util.isolated_popen
        calls = []
        def spawn(cmd, **kwargs):
            calls.append(kwargs)
            return actual(cmd, **kwargs)
        env = {**os.environ, "ONLY_FIXTURE": "kept"}
        result = []
        with patch.object(child_tee.subprocess_util, "isolated_popen", side_effect=spawn), \
                contextlib.redirect_stdout(output):
            worker = threading.Thread(target=lambda: result.append(child_tee.run(
                [sys.executable, "-c", "import time; print('unflushed'); time.sleep(0.7)"],
                root=self.root, phase="live", env=env, timeout=5)))
            worker.start()
            self.assertTrue(seen.wait(0.5), "output must arrive while the child is still alive")
            self.assertTrue(worker.is_alive())
            worker.join(5)
        self.assertFalse(worker.is_alive())
        self.assertEqual(result[0].returncode, 0)
        self.assertEqual(calls[0]["env"], {**env, "PYTHONUNBUFFERED": "1"})
        self.assertFalse(calls[0]["start_new_session"])
        self.assertEqual(calls[0]["creationflags"], child_tee.subprocess_util.no_window_creationflags())

    def test_utf8_log_cap_edges_keep_exact_small_bytes_head_and_final_tail(self):
        cap = 1024 * 1024  # Independent filesystem contract, not the producer constant.
        for size in (cap - 1, cap, cap + 1):
            with self.subTest(size=size):
                prefix, suffix = "HEAD" + os.linesep, "FINAL" + os.linesep
                overhead = len((prefix + suffix).encode())
                source = ("import sys; size=" + str(size) + "; "
                          f"n=size-{overhead}; "
                          "sys.stdout.write('HEAD\\n'+'é'*(n//2)+'x'*(n%2)+'FINAL\\n')")
                result = self.run_child(source, timeout=10)
                raw = Path(result.log_path).read_bytes()
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.log_errors, [])
                self.assertLessEqual(len(raw), cap)
                self.assertTrue(raw.startswith(prefix.encode()))
                self.assertTrue(raw.endswith(suffix.encode()))
                raw.decode("utf-8")  # Neither retained cut splits a character.
                if size <= cap:
                    n = size - overhead
                    self.assertEqual(raw, (prefix + "é" * (n // 2) + "x" * (n % 2) + suffix).encode())
                else:
                    marker = child_tee.LOG_ELISION.replace("\n", os.linesep).encode()
                    self.assertIn(marker, raw)
                    head, tail = raw.split(marker)
                    self.assertLessEqual(len(tail), 64 * 1024)
                    self.assertGreater(len(head), 900000)

    def test_large_two_pipe_logs_finalize_on_nonzero_exit_and_timeout(self):
        source = ("import sys,time; print('OPENING'); "
                  "exec(\"for i in range(160):\\n print('é'*4096)\\n print('🙂'*4096,file=sys.stderr)\"); "
                  "print('BULK-DONE-STDOUT'); print('BULK-DONE-STDERR',file=sys.stderr); "
                  "print('FINAL-STDOUT'); print('FINAL-STDERR',file=sys.stderr); ")

        def ordered_sinks(first):
            bulk_drained = threading.Barrier(2, timeout=10)
            first_ending = threading.Event()

            class ObservedOutput(io.StringIO):
                def __init__(self, label):
                    super().__init__()
                    self.label = label
                    self.marker = 'FINAL-' + label
                    self.seen = threading.Event()

                def write(self, value):
                    count = super().write(value)
                    if 'BULK-DONE-' + self.label in value:
                        # The real reader logs before presenting to this sink.
                        # Neither reader may log its ending until both bulks
                        # have drained, so both endings belong in one suffix.
                        bulk_drained.wait()
                        if self.label != first and not first_ending.wait(10):
                            raise AssertionError('first stream ending did not arrive')
                    if self.marker in value:
                        self.seen.set()
                        if self.label == first:
                            first_ending.set()
                    return count

            self.out = ObservedOutput('STDOUT')
            self.err = ObservedOutput('STDERR')

        original_popen = child_tee.subprocess_util.isolated_popen

        def timeout_after_output(*args, **kwargs):
            process = original_popen(*args, **kwargs)
            original_wait = process.wait

            def wait(timeout=None):
                if timeout is None:
                    return original_wait()
                deadline = time.monotonic() + 10
                for sink in (self.out, self.err):
                    self.assertTrue(sink.seen.wait(max(0, deadline - time.monotonic())),
                                    "fixture did not deliver " + sink.marker)
                self.assertIsNone(process.poll())
                raise subprocess.TimeoutExpired(process.args, timeout)

            process.wait = wait
            return process

        for first in ('STDOUT', 'STDERR'):
            with self.subTest(first=first):
                before = set((self.root / '.wavefoundry/logs').glob('upgrade-child-*.log'))
                ordered_sinks(first)
                result = self.run_child(source + "sys.exit(7)", timeout=10)
                self.assertEqual(result.returncode, 7)
                self.assertEqual(result.log_errors, [])
                for marker in ('FINAL-STDOUT', 'FINAL-STDERR'):
                    self.assertIn(marker, result.tail)
                ordered_sinks(first)
                with self.assertRaises(subprocess.CalledProcessError) as failed:
                    self.run_child(source + "sys.exit(9)", check=True, timeout=10)
                self.assertEqual(failed.exception.returncode, 9)
                # Inject only after both endings: this tests finalization, while
                # the separate withheld-pipe control tests real deadline expiry.
                ordered_sinks(first)
                with patch.object(child_tee.subprocess_util, "isolated_popen", timeout_after_output):
                    with self.assertRaises(subprocess.TimeoutExpired):
                        self.run_child(source + "time.sleep(30)", timeout=2)
                logs = set((self.root / '.wavefoundry/logs').glob('upgrade-child-*.log')) - before
                self.assertEqual(len(logs), 3)
                for log in logs:
                    raw = log.read_bytes()
                    raw.decode('utf-8')  # Retained cuts must not split multibyte text.
                    self.assertLessEqual(len(raw), 1024 * 1024)
                    self.assertIn(b'OPENING', raw)
                    marker = child_tee.LOG_ELISION.replace('\n', os.linesep).encode()
                    self.assertIn(marker, raw)
                    head, tail = raw.split(marker)
                    self.assertGreater(len(head), 900000)
                    self.assertLessEqual(len(tail), 64 * 1024)
                    self.assertIn(b'FINAL-STDOUT', tail)
                    self.assertIn(b'FINAL-STDERR', tail)
                    second = 'STDERR' if first == 'STDOUT' else 'STDOUT'
                    self.assertLess(tail.index(('FINAL-' + first).encode()),
                                    tail.index(('FINAL-' + second).encode()))

    def test_final_log_io_error_is_reported_and_both_pipes_still_drain(self):
        actual = child_tee._open_child_log
        handles = []
        class FinalFailure:
            def __init__(self, handle):
                self.handle = handle
            def write(self, value):
                if "child log output elided" in value:
                    raise OSError("fixture final append failure")
                return self.handle.write(value)
            def flush(self):
                return self.handle.flush()
            def close(self):
                self.handle.close()
        def opened(*args):
            handle, path = actual(*args)
            handles.append(handle)
            return FinalFailure(handle), path
        with patch.object(child_tee, "_open_child_log", side_effect=opened):
            result = self.run_child("import sys; [print('x'*4096) for _ in range(300)]; print('FINAL-OUT'); print('FINAL-ERR',file=sys.stderr)", timeout=10)
        self.assertEqual(result.returncode, 0)
        self.assertIn("OSError", result.log_errors)
        self.assertIn("FINAL-OUT", result.tail)
        self.assertIn("FINAL-ERR", result.tail)
        self.assertTrue(handles[0].closed)

    def test_windows_newline_bytes_are_preserved_and_counted_before_cap(self):
        cap = 1024 * 1024
        for size in (cap - 1, cap, cap + 1):
            with self.subTest(size=size), patch.object(child_tee.os, "linesep", "\r\n"):
                source = ("import sys; size=" + str(size) + "; "
                          "n=size-len(b'HEAD\\r\\nFINAL\\r\\n'); "
                          "sys.stdout.write('HEAD\\n'+'é'*(n//2)+'x'*(n%2)+'FINAL\\n')")
                result = self.run_child(source, timeout=10)
                raw = Path(result.log_path).read_bytes()
                self.assertLessEqual(len(raw), cap)
                self.assertTrue(raw.startswith(b"HEAD\r\n"))
                self.assertTrue(raw.endswith(b"FINAL\r\n"))
                self.assertNotIn(b"\r\r\n", raw)
                if size <= cap:
                    n = size - len(b"HEAD\r\nFINAL\r\n")
                    self.assertEqual(raw, ("HEAD\r\n" + "é" * (n // 2) + "x" * (n % 2) + "FINAL\r\n").encode())
                else:
                    self.assertIn(child_tee.LOG_ELISION.replace("\n", "\r\n").encode(), raw)

    def test_failed_presentation_sink_still_drains_with_bounded_errors(self):
        class ClosedSink:
            def write(self, value):
                raise ValueError('presentation closed')
            def flush(self):
                raise ValueError('presentation closed')
        with patch.object(sys, 'stdout', ClosedSink()), contextlib.redirect_stderr(self.err):
            result = child_tee.run([sys.executable, '-c', "import sys; [print('x'*4096) for _ in range(200)]; print('drained last',file=sys.stderr)"], root=self.root, phase='broken-sink', timeout=10)
        self.assertEqual(result.returncode, 0)
        self.assertIn('drained last', result.tail)
        self.assertLessEqual(len(result.log_errors), 8)
        self.assertEqual(set(result.log_errors), {'ValueError'})
        self.assertIn('drained last', Path(result.log_path).read_text())

    def test_finite_presentation_stall_does_not_hold_log_bookkeeping_lock(self):
        entered, release, other_stream = threading.Event(), threading.Event(), threading.Event()
        class StalledSink(io.StringIO):
            def write(self, value):
                entered.set()
                if not release.wait(3):
                    raise ValueError("fixture presentation deadline")
                return super().write(value)
        class OtherSink(io.StringIO):
            def write(self, value):
                if "other-stream" in value:
                    other_stream.set()
                return super().write(value)
        results = []
        with contextlib.redirect_stdout(StalledSink()), contextlib.redirect_stderr(OtherSink()):
            worker = threading.Thread(target=lambda: results.append(child_tee.run(
                [sys.executable, "-c", "import sys,time; print('stalled'); time.sleep(.1); print('other-stream',file=sys.stderr)"],
                root=self.root, phase="finite-sink")))
            worker.start()
            try:
                self.assertTrue(entered.wait(1))
                self.assertTrue(other_stream.wait(1), "presentation must not own the log/bookkeeping lock")
            finally:
                release.set()
                worker.join(4)
        self.assertFalse(worker.is_alive())
        self.assertEqual(results[0].returncode, 0)
        self.assertIn("other-stream", Path(results[0].log_path).read_text())

    def test_windows_pipe_readiness_abi_eof_error_and_cancellation_are_simulated(self):
        import ctypes
        from ctypes import wintypes
        from unittest.mock import Mock
        handle = 0x123456789ABCDEF if ctypes.sizeof(ctypes.c_void_p) == 8 else 0x12345678
        pipe = Mock()
        pipe.fileno.return_value = 42
        get_handle = Mock(return_value=handle)
        class Peek:
            available, success = 7, True
            def __call__(self, h, buffer, size, read, total, left):
                self.last_handle = h.value
                self.last_args = (buffer, size, read, left)
                total._obj.value = self.available
                return self.success
        peek = Peek()
        kernel = types.SimpleNamespace(PeekNamedPipe=peek)
        stopped = threading.Event()
        with patch.object(child_tee.os, "name", "nt"), \
                patch.dict(sys.modules, {"msvcrt": types.SimpleNamespace(get_osfhandle=get_handle)}), \
                patch.object(ctypes, "WinDLL", return_value=kernel, create=True) as dll, \
                patch.object(ctypes, "get_last_error", return_value=109, create=True) as last_error, \
                patch.object(ctypes, "WinError", side_effect=lambda n: OSError(n, "Windows error"), create=True) as win_error, \
                patch.object(child_tee.os, "read", return_value=b"payload") as read:
            self.assertEqual(child_tee._read_chunk(pipe, stopped), b"payload")
            dll.assert_called_once_with("kernel32", use_last_error=True)
            get_handle.assert_called_once_with(42)
            self.assertEqual(peek.last_handle, handle)
            self.assertEqual(peek.last_args, (None, 0, None, None))
            self.assertEqual(peek.argtypes[0], wintypes.HANDLE)
            self.assertEqual(peek.restype, wintypes.BOOL)
            self.assertEqual(len(peek.argtypes), 6)
            read.assert_called_once_with(42, 7)
            peek.success = False
            for error in (109, 232):
                last_error.return_value = error
                self.assertEqual(child_tee._read_chunk(pipe, stopped), b"")
            last_error.return_value = 5
            with self.assertRaises(OSError) as failed:
                child_tee._read_chunk(pipe, stopped)
            self.assertEqual(failed.exception.errno, 5)
            win_error.assert_called_once_with(5)
            peek.success, peek.available = True, 0
            with patch.object(stopped, "wait", side_effect=lambda delay: stopped.set()) as wait:
                self.assertEqual(child_tee._read_chunk(pipe, stopped), b"")
            wait.assert_called_once_with(.05)
            self.assertEqual(read.call_count, 1)

    def test_none_streams_and_timeout_cleanup(self):
        with patch.object(sys, "stdout", None), patch.object(sys, "stderr", None):
            result = child_tee.run([sys.executable, "-c", "print('windowless')"], root=self.root, phase="none")
        self.assertIn("windowless", Path(result.log_path).read_text())
        start = time.monotonic()
        with self.assertRaises(subprocess.TimeoutExpired):
            self.run_child("import time; print('started'); time.sleep(20)", timeout=0.1)
        self.assertLess(time.monotonic() - start, 4)

    def test_token_split_reads_and_cap_and_controls_never_reach_destinations(self):
        token = "publisher-secret-0123456789"
        source = "import os,time,sys; t=os.environ['WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN']; os.write(1,b'x'*4090+t[:8].encode()); time.sleep(.05); os.write(1,t[8:].encode()+b'\\x1b[31m\\r\\x00\\n'); print(t,file=sys.stderr); sys.exit(1)"
        result = self.run_child(source, env={**os.environ, "WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN": token})
        for value in (self.out.getvalue(), self.err.getvalue(), result.tail, Path(result.log_path).read_text()):
            self.assertNotIn(token, value)
            self.assertNotIn(token[:8], value)
            self.assertNotIn("\x1b", value)
            self.assertNotIn("\r", value)
            self.assertNotIn("\x00", value)
            self.assertNotIn("[31m", value)
        self.assertIn("[REDACTED]", self.out.getvalue())

    def test_decorated_token_canonicalization_spans_reads_and_forced_caps(self):
        token = "0123456789abcdef" * 4  # Realistic publisher UUID-hex token shape.
        controls = ("\x1b[31m", "\x1b]0;title\x07", "\x1b]0;title\x1b\\", "\x00", "\x85")
        for control in controls:
            with self.subTest(control=repr(control)):
                self.out.seek(0); self.out.truncate()
                self.err.seek(0); self.err.truncate()
                parts = ["x" * 4090 + token[:31] + control[:2],
                         control[2:] + token[31:] + "\n"]
                source = ("import os,time,sys; "
                          f"parts={parts!r}; "
                          "[(os.write(fd,p.encode()),time.sleep(.03)) for fd in (1,2) for p in parts]; sys.exit(7)")
                result = self.run_child(source, capture_output=True,
                                        env={**os.environ, "WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN": token})
                self.assertEqual(result.returncode, 7)
                for value in (self.out.getvalue(), self.err.getvalue(), result.stdout,
                              result.stderr, result.tail, Path(result.log_path).read_text()):
                    self.assertNotIn(token, value)
                    self.assertNotIn(token[:31], value)
                    self.assertNotIn(token[31:], value)
                    self.assertIn("[REDACTED]", value)
                    self.assertNotIn("\x1b", value)
                    self.assertNotIn("\x00", value)
                    self.assertNotIn("\x85", value)
                    self.assertNotIn("title", value)
        # Exercise unfinished control state and final-form overlap one byte at
        # a time, without relying on the OS choosing a particular read boundary.
        emitted = []
        lines = child_tee._Lines(token, emitted.append)
        decorated = "x" * 4090 + token[:31] + "\x1b]0;title\x1b\\" + token[31:]
        for char in decorated:
            lines.feed(char)
            self.assertLessEqual(len(lines.pending), child_tee.LINE_CAP_CHARS + len(token))
            self.assertLessEqual(lines.escape_chars, child_tee.LINE_CAP_CHARS)
        lines.feed("", final=True)
        self.assertNotIn(token, "".join(emitted))
        self.assertIn("[REDACTED]", "".join(emitted))
        for control in controls:
            self.assertEqual(child_tee.clean_output(token[:31] + control + token[31:], token), "[REDACTED]")

    def test_default_capture_waits_for_finite_descendant_eof(self):
        marker = self.root / "descendant-finished"
        descendant = ("import pathlib,time,sys; time.sleep(3.2); "
                      "print('LATE-STDOUT'); print('LATE-STDERR',file=sys.stderr); "
                      f"pathlib.Path({str(marker)!r}).write_text('finished')")
        parent = f"import subprocess,sys; subprocess.Popen([sys.executable,'-c',{descendant!r}]); print('EARLY-PARENT')"
        actual = child_tee.subprocess_util.isolated_popen
        children = []
        def spawn(*args, **kwargs):
            process = actual(*args, **kwargs)
            children.append(process)
            return process
        before = set(threading.enumerate())
        start = time.monotonic()
        with patch.object(child_tee.subprocess_util, "isolated_popen", side_effect=spawn):
            result = self.run_child(parent, capture_output=True)
        self.assertGreaterEqual(time.monotonic() - start, 3.2)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(marker.read_text(), "finished")
        self.assertEqual(result.log_errors, [])
        for value in (result.stdout, self.out.getvalue(), result.tail, Path(result.log_path).read_text()):
            self.assertIn("LATE-STDOUT", value)
        for value in (result.stderr, self.err.getvalue(), result.tail, Path(result.log_path).read_text()):
            self.assertIn("LATE-STDERR", value)
        self.assertTrue(children[0].stdout.closed)
        self.assertTrue(children[0].stderr.closed)
        self.assertEqual(children[0].poll(), 0)
        self.assertFalse(set(threading.enumerate()) - before)

    def test_explicit_timeout_includes_withheld_descendant_pipes_and_closes_readers(self):
        release, finished = self.root / "release", self.root / "finished"
        ready = self.root / "ready"
        descendant = ("import pathlib,time; "
                      f"release=pathlib.Path({str(release)!r}); "
                      f"pathlib.Path({str(ready)!r}).write_text('ready'); "
                      "deadline=time.monotonic()+30; "
                      "exec('while not release.exists() and time.monotonic()<deadline: time.sleep(.02)'); "
                      f"pending=pathlib.Path({str(self.root / 'finished.pending')!r}); "
                      "pending.write_text('finished'); "
                      f"pending.replace({str(finished)!r})")
        parent = f"import subprocess,sys; subprocess.Popen([sys.executable,'-c',{descendant!r}]); print('EARLY-PARENT')"
        actual = child_tee.subprocess_util.isolated_popen
        children = []
        def spawn(*args, **kwargs):
            nonlocal start
            process = actual(*args, **kwargs)
            children.append(process)
            # Establish the held-pipe state before run() starts its real .2s
            # deadline. Parent startup is not the behavior this control tests.
            setup_deadline = time.monotonic() + 10
            try:
                self.assertEqual(process.wait(timeout=10), 0)
                while not ready.exists() and time.monotonic() < setup_deadline:
                    time.sleep(.02)
                self.assertTrue(ready.exists(), "descendant did not become ready")
            except BaseException:
                if process.poll() is None:
                    process.kill()
                process.wait()
                raise
            start = time.monotonic()
            return process
        before = set(threading.enumerate())
        start = time.monotonic()
        try:
            with patch.object(child_tee.subprocess_util, "isolated_popen", side_effect=spawn):
                with self.assertRaises(subprocess.TimeoutExpired) as raised:
                    self.run_child(parent, capture_output=True, timeout=.2)
            self.assertEqual(raised.exception.timeout, .2)
            self.assertLess(time.monotonic() - start, 2)
            self.assertEqual(children[0].poll(), 0)  # Parent already exited normally.
            self.assertTrue(children[0].stdout.closed)
            self.assertTrue(children[0].stderr.closed)
            self.assertFalse(set(threading.enumerate()) - before)
            self.assertFalse(finished.exists(), "the timeout must cover still-held pipes")
        finally:
            release.write_text("release")  # Fixture-owned descendant exits naturally.
            if ready.exists():
                deadline = time.monotonic() + 3
                while not finished.exists() and time.monotonic() < deadline:
                    time.sleep(.02)
                self.assertTrue(finished.exists(), "ready descendant did not finish after release")
                self.assertEqual(finished.read_text(), "finished")

    def test_check_true_preserves_nonzero_code_and_complete_canonical_output(self):
        token = "0123456789abcdef" * 4
        source = f"import sys; print({token[:31] + chr(0) + token[31:]!r}); print('failure reason',file=sys.stderr); sys.exit(7)"
        with self.assertRaises(subprocess.CalledProcessError) as failed:
            self.run_child(source, check=True, capture_output=True,
                           env={**os.environ, "WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN": token})
        self.assertEqual(failed.exception.returncode, 7)
        self.assertIn("[REDACTED]", failed.exception.stdout)
        self.assertNotIn(token, failed.exception.stdout)
        self.assertIn("failure reason", failed.exception.stderr)

    def test_failed_retention_closes_the_already_acquired_handle(self):
        handles = []
        actual = cf.open_contained_append
        def opened(*args, **kwargs):
            handle = actual(*args, **kwargs)
            handles.append(handle)
            return handle
        with patch.object(cf, "open_contained_append", side_effect=opened), \
                patch.object(child_tee, "_prune", side_effect=OSError("removed directory")) as prune:
            with self.assertRaises(OSError):
                child_tee._open_child_log(self.root, "retention")
        prune.assert_called_once()
        self.assertEqual(len(handles), 1)
        self.assertTrue(handles[0].closed)

    def test_locked_collision_retries_and_run_group_retention(self):
        actual = cf.open_contained_append
        calls = []
        def locked(root, path, **kwargs):
            calls.append(path)
            if len(calls) == 1:
                raise PermissionError("sharing violation")
            return actual(root, path, **kwargs)
        with patch.object(cf, "open_contained_append", side_effect=locked):
            result = self.run_child("print('retained')")
        self.assertTrue(result.log_path.endswith("-1.log"))
        handle, another = child_tee._open_child_log(self.root, "fixture")
        handle.close()
        self.assertTrue(str(another).endswith("-0.log"))
        handle, collision = child_tee._open_child_log(self.root, "fixture")
        handle.close()
        self.assertTrue(str(collision).endswith("-2.log"))
        self.assertIn("retained", Path(result.log_path).read_text())
        foreign = self.root / ".wavefoundry/logs/foreign.log"
        foreign.write_text("foreign")
        for n in range(7):
            group = f"{n:020d}-{'a'*32}"
            for phase in ("one", "two"):
                (foreign.parent / f"upgrade-child-{group}-{phase}-0.log").write_text(str(n))
        if os.name != "nt":
            link = foreign.parent / f"upgrade-child-{'0'*20}-{'b'*32}-linked-0.log"
            link.symlink_to(foreign)
        child_tee._prune(self.root, child_tee._run_id(self.root))
        groups = {m[1] for path in foreign.parent.iterdir() if path.is_file() and not path.is_symlink()
                  if (m := child_tee._LOG_NAME.fullmatch(path.name))}
        self.assertEqual(len(groups), 5)
        self.assertIn(child_tee._run_id(self.root), groups)
        self.assertEqual(foreign.read_text(), "foreign")
        if os.name != "nt":
            self.assertTrue(link.is_symlink())


if __name__ == "__main__":
    unittest.main()
