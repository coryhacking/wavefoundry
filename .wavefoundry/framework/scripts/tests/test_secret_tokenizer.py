"""Offline tokenizer goldens, asset integrity and bounded failure behavior."""
from __future__ import annotations

import json
import gzip
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wave_lint_lib import secret_tokenizer as tokens


class TestTokenFilters(unittest.TestCase):
    def test_deterministic_multilingual_go_oracle(self):
        path = Path(__file__).parent / "fixtures" / "betterleaks" / "token-oracle.json.gz"
        corpus = json.loads(gzip.decompress(path.read_bytes()))
        self.assertEqual(len(corpus["cases"]), 2006)
        for index, case in enumerate(corpus["cases"]):
            with self.subTest(index=index):
                self.assertEqual(tokens.token_count(case["text"]), case["count"])

    def test_pinned_go_token_counts(self):
        cases = {"": 0, "MIGRATE_HELM_2TO3": 9, "linkedinX9qB2mK7pR4zT8": 15,
                 "this-is-a-long-readable-placeholder-value": 7,
                 "ghp_aB3dE5fG7hI9jK1mN3pQ5rS7tU9vW1xY3zA5": 38,
                 "line one\r\nline two\n\nline three": 8, "<|endoftext|>": 7,
                 "こんにちは世界": 4, "🔐 secrets café": 5, "a" * 1000: 125}
        for text, expected in cases.items():
            with self.subTest(text=text[:40]):
                self.assertEqual(tokens.token_count(text), expected)

    def test_ratio_uses_bytes_and_short_newline_normalization(self):
        self.assertEqual(tokens.token_ratio("é"), 2)
        self.assertEqual(tokens.token_ratio("ab\ncd"), tokens.token_ratio("abcd"))
        self.assertEqual(tokens.token_ratio(""), 0)
        self.assertFalse(tokens.fails_token_efficiency(""))
        self.assertTrue(tokens.fails_token_efficiency("linkedinX9qB2mK7pR4zT8"))
        self.assertFalse(tokens.fails_token_efficiency("ghp_aB3dE5fG7hI9jK1mN3pQ5rS7tU9vW1xY3zA5"))

    def test_entropy_counts_bytes(self):
        self.assertEqual(tokens.entropy("é"), 1)
        self.assertEqual(tokens.entropy(""), 0)
        self.assertEqual(tokens.entropy("aaaa"), 0)

    def test_token_work_is_bounded(self):
        with self.assertRaises(tokens.TokenizerError):
            tokens.token_count("a" * (tokens.MAX_TOKEN_BYTES + 1))
        with patch.object(tokens, "MAX_MERGE_WORK", 1), self.assertRaises(tokens.TokenizerError):
            tokens.token_count("not-a-cached-token-" * 40)


class TestAssetIntegrity(unittest.TestCase):
    def tearDown(self):
        tokens.verify_assets()

    def test_assets_are_pinned_and_missing_assets_fail(self):
        self.assertEqual(len(tokens.verify_assets()), 4)
        with tempfile.TemporaryDirectory() as tmp, patch.object(tokens, "ASSET_ROOT", Path(tmp)):
            with self.assertRaises(tokens.AssetError):
                tokens.verify_assets()

    def test_cached_path_is_rechecked_after_content_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(tokens.ASSET_ROOT, root, dirs_exist_ok=True)
            with patch.object(tokens, "ASSET_ROOT", root):
                tokens.verify_assets()
                asset = root / "words.txt.gz"
                data = asset.read_bytes()
                asset.write_bytes(data[:-1] + bytes((data[-1] ^ 1,)))
                with self.assertRaises(tokens.AssetError):
                    tokens.verify_assets()
                with self.assertRaises(tokens.AssetError):
                    tokens.token_count("a")

    def test_manifest_and_notice_are_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(tokens.ASSET_ROOT, root, dirs_exist_ok=True)
            manifest = root / "manifest.json"
            data = json.loads(manifest.read_text())
            data["assets"]["words.txt.gz"]["uncompressed_bytes"] += 1
            manifest.write_text(json.dumps(data))
            with patch.object(tokens, "ASSET_ROOT", root), self.assertRaises(tokens.AssetError):
                tokens.verify_assets()
            shutil.copy(tokens.ASSET_ROOT / "manifest.json", manifest)
            (root / "NOTICE.md").write_text("corrupt")
            with patch.object(tokens, "ASSET_ROOT", root), self.assertRaises(tokens.AssetError):
                tokens.verify_assets()

    def test_oversized_asset_fails_before_decompression(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(tokens.ASSET_ROOT, root, dirs_exist_ok=True)
            (root / "words.txt.gz").write_bytes(b"x" * 1048577)
            with patch.object(tokens, "ASSET_ROOT", root), self.assertRaises(tokens.AssetError):
                tokens.verify_assets()


if __name__ == "__main__":
    unittest.main()
