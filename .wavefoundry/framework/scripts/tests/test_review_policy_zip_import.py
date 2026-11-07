#!/usr/bin/env python3
"""The lifecycle and upgrade import path loads from a zipped framework (wave 22r99, change 22r98).

``review_policy`` hashes ``gardener_metadata``'s source at import. Under zipimport
that module's ``__file__`` lies inside the archive, so the bytes are read through the
module loader rather than the filesystem.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
from framework_files import framework_source_files  # noqa: E402

# argv[1] is the import root (a zip or the scripts directory). Paths travel through
# argv, never through the program text.
_PROBE = """\
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import review_policy, lifecycle_gate_support, gardener_metadata
old_form = "ok"
try:
    Path(gardener_metadata.__file__).read_bytes()
except NotADirectoryError:
    old_form = "NotADirectoryError"
print(json.dumps({
    "review_policy": review_policy.__file__,
    "lifecycle_gate_support": lifecycle_gate_support.__file__,
    "signature": review_policy.normalizer_signature(),
    "old_form": old_form,
}))
"""


def _probe(import_root: Path) -> dict:
    env = dict(os.environ)
    env.pop("PYTHONPYCACHEPREFIX", None)
    done = subprocess.run(
        [sys.executable, "-B", "-c", _PROBE, str(import_root)],
        capture_output=True, text=True, env=env, timeout=60, cwd=str(import_root.parent),
    )
    if done.returncode != 0:
        raise AssertionError(f"probe failed ({done.returncode}):\n{done.stderr}")
    return json.loads(done.stdout.strip().splitlines()[-1])


class ZippedFrameworkImportTests(unittest.TestCase):
    def test_review_policy_and_lifecycle_gate_support_import_from_a_sources_zip(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "framework-scripts.zip"
            with zipfile.ZipFile(archive, "w") as zipped:
                # The shippable tree: flat modules, their aliases and the package.
                for source in framework_source_files(include_aliases=True):
                    zipped.write(source, source.relative_to(SCRIPTS).as_posix())
            from_zip = _probe(archive)
            from_tree = _probe(SCRIPTS)
        prefix = str(archive) + os.sep
        self.assertTrue(from_zip["review_policy"].startswith(prefix), from_zip)
        self.assertTrue(from_zip["lifecycle_gate_support"].startswith(prefix), from_zip)
        self.assertEqual(from_zip["signature"], from_tree["signature"])
        # The signature is the hash of the normalizer module's own source bytes.
        self.assertEqual(from_tree["signature"],
                         hashlib.sha256((SCRIPTS / "gardener_metadata.py").read_bytes()).hexdigest())
        # Known-bad control: the previous filesystem read cannot work from the zip.
        self.assertEqual(from_zip["old_form"], "NotADirectoryError")
        self.assertEqual(from_tree["old_form"], "ok")


if __name__ == "__main__":
    unittest.main()
