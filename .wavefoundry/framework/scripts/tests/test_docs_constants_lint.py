"""Wave 1seax (1seau): docs-vs-code constants lint + scaffolding integrity."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SCRIPTS_ROOT.parents[2]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from wave_lint_lib.docs_constants_validators import (  # noqa: E402
    _module_constant,
    check_docs_constants,
    check_wave_scaffolding_integrity,
)
import public_contract  # noqa: E402


class PublicContractTests(unittest.TestCase):
    """AC-3: one source of truth, consumed by the handlers."""

    def test_indexer_cli_subset_derives_from_the_module(self):
        import importlib.util
        # AST-level: indexer.py must import CONTENT_CHOICES from public_contract,
        # not re-author the tuple.
        source = (SCRIPTS_ROOT / "indexer.py").read_text(encoding="utf-8")
        self.assertIn(
            "from public_contract import INDEXER_CLI_CONTENT_CHOICES as CONTENT_CHOICES",
            source,
        )

    def test_server_handler_consumes_the_module(self):
        source = (SCRIPTS_ROOT / "server_impl.py").read_text(encoding="utf-8")
        self.assertIn("from public_contract import INDEX_BUILD_CONTENT_VALUES", source)
        self.assertNotIn(
            'content not in {"docs", "code", "all", "graph", "map", "fts"}',
            source,
            "the hand-written vocabulary literal must not return",
        )

    def test_cli_subset_is_a_subset_of_the_public_surface(self):
        self.assertTrue(
            set(public_contract.INDEXER_CLI_CONTENT_CHOICES)
            < set(public_contract.INDEX_BUILD_CONTENT_VALUES)
        )

    def test_handlers_consume_the_vocabulary_aliases(self):
        """Operator-review repair (second pass): the emitting sites consume
        tuple-unpacked aliases of the canonical vocabularies. The first pin
        only rejected direct ``fallback_reason = "..."`` assignments and
        missed producer call arguments, comparisons, and failure_reason dict
        values (model_unavailable / index_missing drifted out of the tuple
        entirely). The repaired pin is indirection-proof: ZERO double-quoted
        occurrences of any canonical reason value anywhere in server_impl —
        every shape (assignment, call argument, comparison, dict value,
        docstring) must go through the aliases."""
        source = (SCRIPTS_ROOT / "server_impl.py").read_text(encoding="utf-8")
        for required in (
            "_FRESHNESS_CURRENT, _FRESHNESS_STALE, _FRESHNESS_UNKNOWN = _INDEX_FRESHNESS_STATES",
            "_MODE_LEXICAL_FALLBACK, _MODE_LIVE_FALLBACK) = _SEARCH_MODES",
            "(_REASON_INDEX_NOT_READY, _REASON_STORE_ABSENT, _REASON_QUERY_FAILED,\n"
            " _REASON_MODEL_UNAVAILABLE, _REASON_INDEX_MISSING) = _LEXICAL_FALLBACK_REASONS",
        ):
            self.assertIn(required, source)
        import public_contract as pc
        for value in pc.LEXICAL_FALLBACK_REASONS:
            self.assertEqual(
                source.count(f'"{value}"'), 0,
                f"quoted fallback-reason value returned to server_impl: \"{value}\"",
            )
        for line in source.splitlines():
            stripped = line.strip()
            self.assertFalse(
                stripped.startswith('search_mode = "'),
                f"bare search_mode literal returned: {stripped}",
            )
            self.assertFalse(
                stripped.startswith('fallback_reason = "'),
                f"bare fallback_reason literal returned: {stripped}",
            )

    def test_lexical_fallback_reasons_cover_every_emitting_site(self):
        """The census that grew LEXICAL_FALLBACK_REASONS from 3 to 5: the
        operator review found model_unavailable and index_missing emitted as
        public fallback_reason values but absent from the canonical tuple."""
        import public_contract as pc
        self.assertEqual(
            pc.LEXICAL_FALLBACK_REASONS,
            ("index_not_ready", "store_absent", "query_failed",
             "model_unavailable", "index_missing"),
        )

    def test_search_modes_cover_every_emitting_site(self):
        """The census that grew SEARCH_MODES from 2 to 5: every mode alias in
        the canonical tuple is actually used, and no sixth mode hides."""
        import public_contract as pc
        self.assertEqual(
            pc.SEARCH_MODES,
            ("semantic", "exact", "hybrid", "lexical_fallback", "live_fallback"),
        )

    def test_ast_constant_extraction_matches_live_values(self):
        self.assertEqual(
            _module_constant("index_state_store.py", "STATE_STORE_SCHEMA_VERSION"),
            __import__("index_state_store").STATE_STORE_SCHEMA_VERSION,
        )


class DocsConstantsLintTests(unittest.TestCase):
    """AC-3: seeded drift fails; the refreshed docs pass."""

    def _seed(self, root: Path, perf: str, rel: str) -> None:
        target = root / "docs" / "architecture" / "performance-budget.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(perf, encoding="utf-8")
        rel_doc = root / "docs" / "RELIABILITY.md"
        rel_doc.parent.mkdir(parents=True, exist_ok=True)
        rel_doc.write_text(rel, encoding="utf-8")

    def test_live_repo_docs_pass(self):
        self.assertEqual(check_docs_constants(REPO_ROOT), [])

    def test_seeded_wrong_model_name_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            live_perf = (REPO_ROOT / "docs" / "architecture" / "performance-budget.md").read_text(encoding="utf-8")
            live_rel = (REPO_ROOT / "docs" / "RELIABILITY.md").read_text(encoding="utf-8")
            drifted = live_perf.replace(
                "docs embedding model `Snowflake/snowflake-arctic-embed-xs`",
                "docs embedding model `sentence-transformers/all-MiniLM-L6-v2`",
            )
            self.assertNotEqual(drifted, live_perf, "seed must actually drift")
            self._seed(root, drifted, live_rel)
            failures = check_docs_constants(root)
            self.assertTrue(any("docs embedding model" in f and "does not match" in f
                               for f in failures), failures)

    def test_dropped_claim_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            live_perf = (REPO_ROOT / "docs" / "architecture" / "performance-budget.md").read_text(encoding="utf-8")
            live_rel = (REPO_ROOT / "docs" / "RELIABILITY.md").read_text(encoding="utf-8")
            dropped = live_rel.replace("index_freshness states: `current/stale/unknown`", "")
            self._seed(root, live_perf, dropped)
            failures = check_docs_constants(root)
            self.assertTrue(any("index_freshness states" in f and "missing" in f
                               for f in failures), failures)

    def test_absent_docs_are_out_of_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(check_docs_constants(Path(tmp)), [])


class ScaffoldingIntegrityTests(unittest.TestCase):
    """AC-5: fixtures are this session's actual defect shapes."""

    def _wave(self, root: Path, wave_id: str, status: str, signoff_line: str) -> Path:
        d = root / "docs" / "waves" / wave_id
        d.mkdir(parents=True, exist_ok=True)
        (d / "wave.md").write_text(
            f"# Wave Record\n\nStatus: {status}\n\nwave-id: `{wave_id}`\n\n"
            f"## Review Evidence\n\n{signoff_line}\n",
            encoding="utf-8",
        )
        return d

    def test_unbracketed_preapproval_signoff_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # The actual defect: the placeholder pasted WITHOUT its brackets,
            # which the close gate reads as a real approval.
            self._wave(root, "1x live", "active",
                       "- operator-signoff: approved when operator confirms closure")
            failures = check_wave_scaffolding_integrity(root)
            self.assertTrue(any("unbracketed pre-approval" in f for f in failures), failures)

    def test_bracketed_placeholder_and_real_approval_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._wave(root, "1x live", "active",
                       "- operator-signoff: <approved when operator confirms closure>")
            self._wave(root, "1y live", "active",
                       "- operator-signoff: approved")
            self.assertEqual(check_wave_scaffolding_integrity(root), [])

    def test_closed_waves_are_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._wave(root, "1x old", "closed",
                       "- operator-signoff: approved when operator confirms closure")
            self.assertEqual(check_wave_scaffolding_integrity(root), [])

    def test_admitted_doc_wave_tbd_and_mismatch_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = self._wave(root, "1x live", "active",
                           "- operator-signoff: <approved when operator confirms closure>")
            (d / "1abcd-enh thing.md").write_text(
                "# T\n\nChange ID: `1abcd-enh thing`\nWave: TBD\n", encoding="utf-8"
            )
            (d / "1abce-enh other.md").write_text(
                "# T\n\nChange ID: `1abce-enh other`\nWave: `1zzzz wrong-wave`\n",
                encoding="utf-8",
            )
            failures = check_wave_scaffolding_integrity(root)
            self.assertTrue(any("Wave: TBD" in f for f in failures), failures)
            self.assertTrue(any("does not match the containing" in f for f in failures), failures)

    def test_matching_wave_reference_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = self._wave(root, "1x live", "active",
                           "- operator-signoff: <approved when operator confirms closure>")
            (d / "1abcd-enh thing.md").write_text(
                "# T\n\nChange ID: `1abcd-enh thing`\nWave: `1x live`\n", encoding="utf-8"
            )
            self.assertEqual(check_wave_scaffolding_integrity(root), [])

    def test_live_repo_is_clean(self):
        self.assertEqual(check_wave_scaffolding_integrity(REPO_ROOT), [])


if __name__ == "__main__":
    unittest.main()
