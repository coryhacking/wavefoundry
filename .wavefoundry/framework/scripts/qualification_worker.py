"""Opt-in, bounded execution-origin unittest detail; no worker files."""
from __future__ import annotations

import contextlib
import json
import os
import sys
import unittest

# Workers always stay read-only, including direct invocations without -B.
if __name__ == "__main__" or sys.pycache_prefix is None:
    sys.dont_write_bytecode = True
import bytecode_cache  # noqa: E402

if __name__ == "__main__":
    bytecode_cache.configure(read_only=True)

MAX_SKIPS = 20000
MAX_FIELD = 4096
MAX_ENVELOPE = 4 * 1024 * 1024


class QualificationResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.exact_skips = []
        self.issues = set()
        self.markers = {}

    def addSkip(self, test, reason):  # noqa: N802
        super().addSkip(test, reason)
        identity = test.id()
        marker = self.markers.get(identity)
        if len(self.exact_skips) >= MAX_SKIPS or any(
                not isinstance(value, str) or len(value) > MAX_FIELD
                for value in (identity, reason)):
            self.issues.add("skip detail exceeds bound")
            return
        if marker is not None and (not isinstance(marker, str) or len(marker) > MAX_FIELD):
            self.issues.add("default-profile marker exceeds bound")
            marker = None
        self.exact_skips.append({"id": identity, "reason": reason,
                                 "default_profile_only": marker})


def _markers(suite):
    markers = {}
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            markers.update(_markers(test))
        else:
            cls = type(test)
            class_marker = getattr(cls, "__default_profile_only__", None)
            method = getattr(test, getattr(test, "_testMethodName", ""), None)
            markers[test.id()] = getattr(method, "__default_profile_only__", class_marker)
            if class_marker:
                markers[f"setUpClass ({cls.__module__}.{cls.__qualname__})"] = class_marker
    return markers


@contextlib.contextmanager
def _protocol_output():
    # A Python wrapper can be replaced and native isolation can repoint fd 1.
    # Own a non-inheritable duplicate before discovery; never close a borrowed
    # stream when the caller supplies a sink without a usable descriptor.
    borrowed = sys.stdout
    try:
        descriptor = os.dup(borrowed.fileno())
    except (AttributeError, OSError, ValueError):
        yield borrowed
        return
    try:
        stream = os.fdopen(descriptor, "w", encoding="utf-8", newline="\n")
    except BaseException:
        os.close(descriptor)
        raise
    with stream:
        yield stream


def _run(directory, name, nonce, protocol_stream):
    suite = unittest.defaultTestLoader.discover(directory, pattern=name)
    markers = _markers(suite)

    class Result(QualificationResult):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.markers = markers

    result = unittest.TextTestRunner(verbosity=2, resultclass=Result).run(suite)
    payload = {"tests": result.testsRun, "skipped": len(result.skipped),
               "failures": len(result.failures), "errors": len(result.errors),
               "successful": result.wasSuccessful(), "skips": result.exact_skips,
               "issues": sorted(set(result.issues)), "terminal": True}
    encoded = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
    if len(encoded) > MAX_ENVELOPE:
        encoded = json.dumps({"terminal": True, "issues": ["worker envelope exceeds bound"]})
    print(f"\nWF_QUALIFICATION:{nonce}:{encoded}", file=protocol_stream, flush=True)
    return 0 if result.wasSuccessful() else 1


def main():
    directory, name, nonce = sys.argv[1:]
    with _protocol_output() as protocol_stream:
        return _run(directory, name, nonce, protocol_stream)


if __name__ == "__main__":
    raise SystemExit(main())
