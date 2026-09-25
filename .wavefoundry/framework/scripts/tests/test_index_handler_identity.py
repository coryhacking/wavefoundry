"""Moved index module independently participates in retrieval identity."""
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from framework_files import framework_source_files, source_path  # wf_server-aware source locations (wave 1yzd0)
import retrieval_eval


class IndexHandlerIdentityTests(unittest.TestCase):
    def test_index_handler_edit_moves_production_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            scripts = Path(temp)
            # Independent source discovery: removing membership must not also
            # remove the mutated file from the fixture.
            for source in framework_source_files(include_aliases=True):
                (scripts / source.relative_to(SCRIPTS)).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, scripts / source.relative_to(SCRIPTS))
            moved = source_path("index_handlers.py", scripts)  # the implementation, never the alias
            self.assertTrue(moved.is_file())
            before = retrieval_eval._production_identity(scripts)
            moved.write_text(moved.read_text() + "\n# index identity mutation\n")
            after = retrieval_eval._production_identity(scripts)
            self.assertIn("index_handlers.py", before["modules"])
            self.assertNotEqual(before["digest"], after["digest"])


if __name__ == "__main__":
    unittest.main()
