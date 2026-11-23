"""Shared test support for the line-ending rule (wave 244in, change 244fj).

``windows_text_writes()`` simulates native Windows text writes on any host:
a text-mode ``Path.open`` write whose ``newline`` is unset translates each
``\\n`` to ``\\r\\n`` (``Path.write_text`` goes through ``Path.open``), and
``os.linesep`` is ``"\\r\\n"``.  It patches ``Path.open`` only; builtin
``open``, ``os.fdopen`` and ``NamedTemporaryFile`` are covered by the census
rule that every text-mode write sets ``newline``.  This is a simulation, not
native Windows qualification.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

LF = "\n"
CRLF = "\r\n"


@contextmanager
def windows_text_writes():
    """Real I/O with Windows' default write translation and ``os.linesep``."""
    original_open = Path.open

    def open_with_windows_default(path, mode="r", buffering=-1, encoding=None,
                                  errors=None, newline=None):
        if any(flag in mode for flag in "wax+") and "b" not in mode and newline is None:
            newline = CRLF
        return original_open(path, mode, buffering, encoding, errors, newline)

    with mock.patch.object(Path, "open", open_with_windows_default), \
            mock.patch.object(os, "linesep", CRLF):
        yield


def with_endings(lf_text: str, ending: str) -> str:
    """Return ``lf_text`` with every LF replaced by ``ending``."""
    return lf_text.replace(LF, ending)


def mixed(lf_text: str) -> str:
    """A mixed file: the first line LF, every later line CRLF."""
    head, sep, rest = lf_text.partition(LF)
    return head + sep + rest.replace(LF, CRLF)


def assert_no_double_cr(case, data: bytes) -> None:
    case.assertNotIn(b"\r\r\n", data)


# (name, input builder, expected builder) for the three input shapes.
SHAPES = (
    ("lf", lambda text: text, lambda text: text),
    ("crlf", lambda text: with_endings(text, CRLF), lambda text: with_endings(text, CRLF)),
    ("mixed", mixed, mixed),
)


def run_matrix(case, write_input, run_writer, read_output, before_lf: str, after_lf: str):
    """Run one in-place writer over LF, CRLF and mixed inputs, natively and
    under ``windows_text_writes``, asserting exact bytes and no ``\\r\\r\\n``.

    ``before_lf`` and ``after_lf`` are the file's LF text before and after the
    writer.  The mixed shape keeps the first line LF and every other line
    CRLF, so the expected mixed output is ``mixed(after_lf)`` provided the
    writer keeps the first line and the file stays majority CRLF.
    ``write_input(text)`` creates the fixture (fresh state per call),
    ``run_writer()`` runs the writer, and ``read_output()`` returns bytes.
    """
    for shape, build_in, build_out in SHAPES:
        for simulated in (False, True):
            with case.subTest(shape=shape, windows_simulation=simulated):
                write_input(build_in(before_lf))
                if simulated:
                    with windows_text_writes():
                        run_writer()
                else:
                    run_writer()
                data = read_output()
                assert_no_double_cr(case, data)
                case.assertEqual(data, build_out(after_lf).encode("utf-8"))
