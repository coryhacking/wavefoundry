"""Cross-run identity policy and diagnostic purity, without platform claims."""
import copy
import ntpath
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import storage_identity as subject


class IdentityTests(unittest.TestCase):
    def test_platform_matrix(self):
        for stored_inode, live_inode, accepted, basis in (
            (7, 7, True, "path+inode"), (7, 8, False, "path+inode"),
            (0, 7, True, "path"), (7, 0, True, "path"), (0, 0, True, "path"),
        ):
            for device in (1, 9):
                with self.subTest(stored_inode=stored_inode, live_inode=live_inode, device=device):
                    stored = {"device": 1, "inode": stored_inode}
                    live = {"device": device, "inode": live_inode}
                    before = copy.deepcopy((stored, live))
                    self.assertEqual(subject.compare_identity(stored, live), {
                        "matches": accepted, "basis": basis, "device_drift": device != 1,
                    })
                    self.assertEqual(before, (stored, live))

    def test_malformed_never_means_unavailable(self):
        valid = {"device": 1, "inode": 7}
        malformed = [None, {}, [], {"inode": 0}]
        for field in valid:
            for value in (None, -1, "0", True, 0.0):
                malformed.append({**valid, field: value})
        for bad in malformed:
            for pair in ((bad, valid), (valid, bad)):
                with self.subTest(pair=pair):
                    self.assertEqual(subject.compare_identity(*pair)["basis"], "invalid")
                    self.assertFalse(subject.compare_identity(*pair)["matches"])

    def test_resolved_paths_and_simulated_windows_case_rules(self):
        self.assertTrue(subject.same_path("/repo/child/..", "/repo"))
        self.assertFalse(subject.same_path("/repo", "/other"))
        self.assertFalse(subject.same_path("", "/repo"))
        self.assertFalse(subject.same_path(None, "/repo"))
        with patch.object(subject.os.path, "normcase", ntpath.normcase):
            self.assertTrue(subject.same_path("/Repo", "/repo"))
            self.assertFalse(subject.same_path("/Repo", "/different"))


if __name__ == "__main__":
    unittest.main()
