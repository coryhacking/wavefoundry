from __future__ import annotations

import importlib.util
import contextlib
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import sqlite3
import types
import textwrap
import time
import unittest
from contextlib import contextmanager
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, call, patch


SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
INDEXER_PATH = SCRIPTS_ROOT / "indexer.py"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))
from framework_files import framework_source_files  # wf_server-aware source locations (wave 1yzd0)
import index_paths  # noqa: E402 — one definition of the shared database name


def _rmtree_git(path: Path) -> None:
    """Windows-safe ``rmtree`` for a ``.git`` tree: git marks loose objects and
    pack files read-only, so a plain ``shutil.rmtree`` raises ``PermissionError``
    on Windows. Clear the read-only bit and retry; a no-op on POSIX."""
    def _clear(func, p, _exc):
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except OSError:
            pass
    kw = {"onexc": _clear} if sys.version_info >= (3, 12) else {"onerror": _clear}
    shutil.rmtree(path, **kw)


def load_build_index():
    spec = importlib.util.spec_from_file_location("indexer", INDEXER_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["indexer"] = mod
    spec.loader.exec_module(mod)
    return mod


def _make_embedder_mock(dim: int = 384, calls: list[list[str]] | None = None):
    """Deterministic nonzero384D embeddings exercise the actual cosine store."""
    import numpy as np
    def fake_embed(texts,batch_size=256):
        values=list(texts)
        if calls is not None: calls.append(values)
        for text in values:
            vector=np.zeros(384,dtype=np.float32);vector[0]=1;vector[1]=(len(text)%13)/13
            yield vector
    mock=MagicMock();mock.embed.side_effect=fake_embed
    return mock


def _read_index_chunks(index_dir: Path, table_name: str) -> list[dict]:
    import sqlite_vector_store as vectors
    if not (index_dir / vectors.FILENAME).is_file(): return []
    return vectors.payload_rows(index_dir,table_name)


def _store_mod():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "index_state_store", SCRIPTS_ROOT / "index_state_store.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _read_meta_store(index_dir: Path) -> dict:
    """1sed6: build-state reads go through the store (meta.json retired)."""
    return _store_mod().export_meta_snapshot(index_dir) or {}


def _seed_meta_store(index_dir: Path, meta: dict) -> None:
    """1sed6: seed prior-build state the way production records it."""
    _store_mod().write_build_bookkeeping(index_dir, meta)


def _published_graph_payload(bi, root: Path) -> dict:
    """The PUBLISHED graph payload, from the rows.

    Wave 1xny6 lane L6b retired the derived ``project-graph.json`` artifact, so
    a test that used to decode that file reads the rows the build committed.
    """
    snapshot = bi._get_graph_indexer().read_published_graph_snapshot(root, "project")
    assert snapshot is not None, "no published graph generation"
    return snapshot["payload"]


def _make_repo(tmp: Path, files: dict[str, str]) -> None:
    """Write files into a temp repo with a minimal workflow-config.json."""
    (tmp / "docs").mkdir(parents=True, exist_ok=True)
    (tmp / "docs" / "workflow-config.json").write_text(
        json.dumps({"lifecycle_id_policy": {"epoch_utc": "2020-02-02T02:02:00Z", "hour_offset": 0}}),
        encoding="utf-8",
    )
    for rel, content in files.items():
        p = tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


class FileWalkerTests(unittest.TestCase):
    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_walks_python_and_markdown(self):
        _make_repo(self.root, {
            "src/foo.py": "def f(): pass\n",
            "docs/guide.md": "# Guide\n\nContent.\n",
        })
        files = self.bi.walk_repo(self.root)
        names = {f.name for f in files}
        self.assertIn("foo.py", names)
        self.assertIn("guide.md", names)

    def test_memory_archive_bodies_are_excluded_but_register_is_indexable(self):
        _make_repo(self.root, {
            "docs/agents/memory/archive/mem-old.md": "# Archived full body\n",
            "docs/agents/memory/pointers/mem-old.md": "# Retired pointer\n",
            "docs/agents/memory-archive.md": "# Memory archive\n",
            ".wavefoundry/memory-purge-dispositions.json": (
                '{"schema_version":1,"source_event_sha256":[]}\n'
            ),
        })
        rels = {
            str(path.relative_to(self.root)).replace("\\", "/")
            for path in self.bi.walk_repo(self.root)
        }
        self.assertNotIn("docs/agents/memory/archive/mem-old.md", rels)
        self.assertNotIn("docs/agents/memory/pointers/mem-old.md", rels)
        self.assertIn("docs/agents/memory-archive.md", rels)
        self.assertNotIn(".wavefoundry/memory-purge-dispositions.json", rels)
        self.assertTrue(
            self.bi._is_memory_archive_body_path(
                r"docs\agents\memory\archive\mem-old.md"
            )
        )
        self.assertTrue(
            self.bi._is_legacy_memory_pointer_path(
                r"docs\agents\memory\pointers\mem-old.md"
            )
        )

    def test_excludes_only_canonical_wave_event_ledgers(self):
        """1slep AC-8 / 1tomw AC-6: the fixed wave-folder role alone excludes."""
        _make_repo(self.root, {
            "docs/waves/1slep external-ledger/events.jsonl": '{"canonical":true}\n',
            # component-fixture: test_excludes_only_canonical_wave_event_ledgers exercises this input representation directly
            "docs/waves/1slep external-ledger/wave.md": "# Wave\nreview-evidence-source: events.jsonl\n\n# Searchable current-state projection\n",
            "events.jsonl": '{"root":"eligible"}\n',
            "audit/events.jsonl": '{"nested":"eligible"}\n',
            "docs/waves/events.jsonl": '{"no-wave-directory":"eligible"}\n',
            "docs/waves/notes/events.jsonl": '{"wave-folder-role":"excluded"}\n',
            "docs/waves/1slep external-ledger/archive/events.jsonl": '{"deeper":"eligible"}\n',
        })

        rels = {
            str(path.relative_to(self.root)).replace("\\", "/")
            for path in self.bi.walk_repo(self.root)
        }

        self.assertNotIn("docs/waves/1slep external-ledger/events.jsonl", rels)
        self.assertIn("docs/waves/1slep external-ledger/wave.md", rels)
        self.assertIn("events.jsonl", rels)
        self.assertIn("audit/events.jsonl", rels)
        self.assertIn("docs/waves/events.jsonl", rels)
        # FU4: position decides the role, not folder spelling. A ledger in ANY
        # direct child directory of docs/waves/ is excluded, so a renamed wave
        # folder cannot leak its raw ledger into retrieval. (Before FU4 this
        # asserted the opposite: the id-shape clause made "notes" eligible.)
        self.assertNotIn("docs/waves/notes/events.jsonl", rels)
        self.assertIn("docs/waves/1slep external-ledger/archive/events.jsonl", rels)
        self.assertTrue(
            self.bi._is_canonical_wave_events_path(
                r"docs\waves\1slep external-ledger\events.jsonl", self.root
            ),
            "Windows separators must normalize to the same exact path shape",
        )
        self.assertTrue(
            self.bi._is_canonical_wave_events_path(
                "docs/waves/notes/events.jsonl", self.root
            )
        )

    def test_renamed_wave_directory_ledger_stays_excluded(self):
        """FU4 (1to78 follow-up): exclusion is content-role, not name-shape.

        1to78 moved the docs-lint orphan guard to the content role but left
        this retrieval exclusion name-driven, so renaming a wave directory
        (underscore separator, non-id prefix, uppercase, 7-char prefix) made
        the wave's raw ledger index-ELIGIBLE while the wave stayed fully
        live and resolvable. Every direct child directory of docs/waves/
        holding an events.jsonl occupies the wave-folder role regardless of
        how the folder is spelled.
        """
        import review_evidence

        renamed = [
            "1slep_external-ledger",       # underscore separator
            "RENAMED-external-ledger",     # non-id prefix
            "1SLEPX external-ledger",      # uppercase + 7-char prefix
            "notes",                       # bare non-id name
        ]
        _make_repo(self.root, {
            f"docs/waves/{name}/events.jsonl": '{"renamed":true}\n'
            for name in renamed
        })

        rels = {
            str(path.relative_to(self.root)).replace("\\", "/")
            for path in self.bi.walk_repo(self.root)
        }
        for name in renamed:
            rel = f"docs/waves/{name}/events.jsonl"
            self.assertTrue(
                review_evidence.is_canonical_wave_events_path(rel, self.root),
                f"renamed wave folder {name!r} must still occupy the wave-folder role",
            )
            self.assertNotIn(rel, rels, f"{name!r} ledger must not reach the index")

        # The depth and basename bounds are unchanged: only the name-shape
        # clause is dropped, so these stay eligible.
        for still_eligible in (
            "events.jsonl",
            "docs/waves/events.jsonl",
            "docs/waves/1slep external-ledger/archive/events.jsonl",
        ):
            self.assertFalse(
                review_evidence.is_canonical_wave_events_path(
                    still_eligible, self.root
                ),
                f"{still_eligible!r} is not a fixed wave-folder sibling",
            )

    def test_id_shape_hint_is_a_separate_message_only_predicate(self):
        """FU4: the id-shape test survives as a lint MESSAGE hint only.

        The orphan-ledger failure text tells the operator when a folder name
        is not id-shaped ("this may also be a renamed wave directory"). That
        hint must not be re-derived from the role predicate, or making the
        role content-driven would silently delete the hint.
        """
        import review_evidence

        self.assertTrue(
            review_evidence.is_id_shaped_wave_dir_name("1slep external-ledger")
        )
        self.assertTrue(
            review_evidence.is_id_shaped_wave_dir_name("1to78-preship")
        )
        for renamed in ("1slep_external-ledger", "RENAMED-x", "notes", "1SLEPX x"):
            self.assertFalse(
                review_evidence.is_id_shaped_wave_dir_name(renamed), renamed
            )

    def test_wave_ledger_predicate_is_the_single_review_evidence_definition(self):
        """Wave 1to78 (AC-7): predicate sharing is by relocation, not
        duplication: the indexer's exclusion symbol IS review_evidence's
        public predicate (one definition of the fixed wave-folder role for
        both the retrieval exclusion and the docs-lint orphan-ledger guard),
        and the lint consumer binds to that same object.

        FU4 split the id-shape MESSAGE hint into its own symbol. Each
        consumer now binds exactly the predicate it needs, still by
        relocation rather than duplication: the indexer binds the role
        predicate, and lint binds only the hint (it enumerates the role
        itself by content, so it must NOT hold a second role predicate that
        could drift from the indexer's)."""
        import review_evidence
        from wave_lint_lib import wave_validators

        self.assertIs(
            self.bi._is_canonical_wave_events_path,
            review_evidence.is_canonical_wave_events_path,
        )
        self.assertIs(
            wave_validators.is_id_shaped_wave_dir_name,
            review_evidence.is_id_shaped_wave_dir_name,
        )
        self.assertFalse(
            hasattr(wave_validators, "is_canonical_wave_events_path"),
            "lint must not carry a role predicate it does not consume",
        )

    def test_ledger_stays_excluded_after_source_tamper_without_state_lookup(self):
        """1tomw AC-6: declaration tampering cannot admit raw review history.

        The fixed wave-folder role alone decides exclusion — no wave.md read
        and no retained adoption state is consulted, so a removed or wrong
        source declaration changes nothing.
        """
        import review_evidence

        wave_dir = self.root / "docs" / "waves" / "1test declared-ledger"
        _make_repo(self.root, {
            "docs/waves/1test declared-ledger/events.jsonl": "",
            "docs/waves/1test declared-ledger/wave.md": (
                # component-fixture: test_ledger_stays_excluded_after_source_tamper_without_state_lookup exercises this input representation directly
                "# Wave\nreview-evidence-source: events.jsonl\n\n"
                + review_evidence.empty_external_finding_synthesis_section()
            ),
            # Eligible control. FU4 made folder spelling irrelevant to the
            # role, so the contrast is now DEPTH: a ledger nested below the
            # wave folder is not the fixed sibling and stays indexable.
            "docs/waves/1test declared-ledger/archive/events.jsonl": (
                '{"deeper":"eligible"}\n'
            ),
        })
        wave_md = wave_dir / "wave.md"

        for tampered in (
            "# Wave\n\n" + review_evidence.empty_external_finding_synthesis_section(),
            "# Wave\nreview-evidence-source: wrong.jsonl\n\n"
            + review_evidence.empty_external_finding_synthesis_section(),
        ):
            wave_md.write_text(tampered, encoding="utf-8")
            rels = {
                str(path.relative_to(self.root)).replace("\\", "/")
                for path in self.bi.walk_repo(self.root)
            }
            self.assertNotIn(
                "docs/waves/1test declared-ledger/events.jsonl", rels
            )
            self.assertIn(
                "docs/waves/1test declared-ledger/archive/events.jsonl", rels
            )

    def test_excludes_git_directory(self):
        _make_repo(self.root, {"src/foo.py": "x = 1\n"})
        git_file = self.root / ".git" / "config"
        git_file.parent.mkdir(parents=True, exist_ok=True)
        git_file.write_text("git config", encoding="utf-8")
        files = self.bi.walk_repo(self.root)
        self.assertFalse(any(".git" in str(f) for f in files))

    def test_excludes_node_modules(self):
        _make_repo(self.root, {
            "src/foo.py": "x = 1\n",
            "node_modules/pkg/index.js": "module.exports = {};\n",
        })
        files = self.bi.walk_repo(self.root)
        self.assertFalse(any("node_modules" in str(f) for f in files))

    def test_excludes_graphify_output_without_excluding_similarly_named_source(self):
        _make_repo(self.root, {
            "graphify-out/graph.json": '{"nodes": []}\n',
            "graphify-out/GRAPH_REPORT.md": "# Generated report\n",
            "src/graphify-output.ts": "export const source = true;\n",
        })
        rels = {
            str(path.relative_to(self.root)).replace("\\", "/")
            for path in self.bi.walk_repo(self.root)
        }
        self.assertNotIn("graphify-out/graph.json", rels)
        self.assertNotIn("graphify-out/GRAPH_REPORT.md", rels)
        self.assertIn("src/graphify-output.ts", rels)

    def test_prunes_excluded_directories_without_rglob(self):
        _make_repo(self.root, {
            "src/foo.py": "x = 1\n",
            "node_modules/pkg/index.js": "module.exports = {};\n",
            ".git/config": "[core]\nrepositoryformatversion = 0\n",
            "dist/bundle.js": "console.log('ignored');\n",
        })
        with patch.object(Path, "rglob", side_effect=AssertionError("walk_repo should not use rglob")):
            files = self.bi.walk_repo(self.root)
        rels = {str(f.relative_to(self.root)).replace("\\", "/") for f in files}
        self.assertEqual(rels, {"docs/workflow-config.json", "src/foo.py"})


class TimestampedLogTests(unittest.TestCase):
    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_timestamped_stream_prefixes_each_complete_line(self):
        out = io.StringIO()
        stream = self.bi._TimestampedStream(out)

        stream.write("build_index: embedding doc chunks 1-2/2\n")
        stream.write("build_index: index is up to date\n")
        stream.flush()

        lines = out.getvalue().splitlines()
        self.assertEqual(len(lines), 2)
        for line in lines:
            self.assertRegex(line, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00 build_index: ")
        self.assertIn("embedding doc chunks 1-2/2", lines[0])
        self.assertIn("index is up to date", lines[1])

    def test_walk_repo_returns_sorted_paths(self):
        _make_repo(self.root, {
            "z.txt": "z\n",
            "a.txt": "a\n",
            "src/b.txt": "b\n",
            "src/a.txt": "a\n",
            "src/nested/c.txt": "c\n",
        })
        files = self.bi.walk_repo(self.root)
        rels = [str(f.relative_to(self.root)).replace("\\", "/") for f in files]
        self.assertEqual(rels, sorted(rels))

    def test_walk_admits_ignore_files_as_code_sources(self):
        """1seas (wave 1seaw): the direct-artifact rank-one pin needs the named ignore
        file indexed; the seven low-information ignore names are walked, kept by the
        source filter, and chunked as one line-window code unit (WALKER 16)."""
        _make_repo(self.root, {
            "src/foo.py": "x = 1\n",
            ".aiignore": "# runtime\n.wavefoundry/*.lock\n",
            ".gitignore": "dist/\n",
            "pkg/.dockerignore": "node_modules/\n",
            "notes": "extensionless prose\n",
        })
        files = self.bi.walk_repo(self.root)
        rels = {str(f.relative_to(self.root)).replace("\\", "/") for f in files}
        self.assertTrue({".aiignore", ".gitignore", "pkg/.dockerignore"} <= rels, rels)
        # The walk's text sniff admits any extensionless text file; the SOURCE filter is
        # the layer that dropped ignore files before WALKER 16 and still drops arbitrary
        # extensionless prose.
        kept = self.bi._filter_code_files(
            files, self.root, include_tests=False, include_generated=False,
        )
        kept_rels = {str(f.relative_to(self.root)).replace("\\", "/") for f in kept}
        self.assertTrue({".aiignore", ".gitignore", "pkg/.dockerignore", "src/foo.py"} <= kept_rels)
        self.assertNotIn("notes", kept_rels, "arbitrary extensionless files stay out of the code index")
        self.assertEqual(
            {".aiignore", ".dockerignore", ".eslintignore", ".gitignore", ".ignore",
             ".npmignore", ".prettierignore"},
            set(self.bi.CODE_EXTENSIONLESS_NAMES) - {
                "Jenkinsfile", "Makefile", "Dockerfile", "Vagrantfile", "Brewfile",
                "Fastfile", "Appfile", "Podfile", "Gemfile", "Procfile",
            },
        )
        self.assertGreaterEqual(int(self.bi.WALKER_VERSION), 16)
        import importlib
        if str(SCRIPTS_ROOT) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_ROOT))
        ch = importlib.import_module("chunker")
        chunks = ch.chunk_file("# runtime\n.wavefoundry/*.lock\n", ".aiignore")
        self.assertEqual([(".aiignore:L1-L2", "code")], [(c.id, c.kind) for c in chunks])

    def test_excludes_pycache(self):
        _make_repo(self.root, {"src/foo.py": "x = 1\n"})
        cache = self.root / "src" / "__pycache__" / "foo.cpython-312.pyc"
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(b"\x00")
        files = self.bi.walk_repo(self.root)
        self.assertFalse(any("__pycache__" in str(f) for f in files))

    def test_excludes_binary_extensions(self):
        _make_repo(self.root, {"src/foo.py": "x = 1\n"})
        (self.root / "src" / "image.png").write_bytes(b"\x89PNG")
        (self.root / "src" / "data.bin").write_bytes(b"\x93NUMPY")
        files = self.bi.walk_repo(self.root)
        names = {f.name for f in files}
        self.assertNotIn("image.png", names)
        self.assertNotIn("data.bin", names)

    def test_excludes_elf_and_office_binaries(self):
        # AC-1 (12c7n-bug binary-files-indexed-as-text): ELF, EPS, PPTX excluded
        _make_repo(self.root, {"src/app.py": "x = 1\n"})
        (self.root / "src" / "app").write_bytes(b"\x7fELF\x02\x01\x01")
        (self.root / "src" / "slide.pptx").write_bytes(b"PK\x03\x04")
        (self.root / "src" / "logo.eps").write_bytes(b"%!PS-Adobe-3.0 EPSF-3.0\n")
        (self.root / "src" / "icon.png").write_bytes(b"\x89PNG\r\n")
        (self.root / "src" / "diagram.svg").write_bytes(b"<svg></svg>")
        files = self.bi.walk_repo(self.root)
        names = {f.name for f in files}
        self.assertIn("app.py", names)
        self.assertNotIn("slide.pptx", names)
        self.assertNotIn("logo.eps", names)
        self.assertNotIn("icon.png", names)
        self.assertNotIn("diagram.svg", names)

    def test_excludes_null_byte_unknown_extension(self):
        # AC-3 (12c7n-bug binary-files-indexed-as-text): null-byte sniff for unknown extensions
        _make_repo(self.root, {"src/foo.py": "x = 1\n"})
        # Use .myext — not in any known binary or text list
        (self.root / "src" / "data.myext").write_bytes(b"\x00\x01\x02binary data here")
        (self.root / "src" / "config.myext").write_text("key=value\n", encoding="utf-8")
        files = self.bi.walk_repo(self.root)
        names = {f.name for f in files}
        self.assertNotIn("data.myext", names)
        self.assertIn("config.myext", names)

    def test_excludes_elf_extensionless(self):
        # Extensionless ELF binaries (Lambda extension pattern) excluded via magic bytes.
        # Uses no null bytes so null-byte fallback cannot carry this — magic check must fire.
        _make_repo(self.root, {"src/foo.py": "x = 1\n"})
        elf_header = b"\x7fELF" + b"\x01\x01\x01\x03" * 16  # ELF magic + non-null padding
        (self.root / "src" / "AWSSecretsLambdaExtension").write_bytes(elf_header)
        files = self.bi.walk_repo(self.root)
        names = {f.name for f in files}
        self.assertNotIn("AWSSecretsLambdaExtension", names)
        self.assertIn("foo.py", names)

    def test_excludes_lock_files(self):
        # AC-1..AC-3 (12c7n-bug generated-lock-files-indexed): lock files excluded
        _make_repo(self.root, {
            "package.json": '{"name":"app"}',
            "src/index.ts": "export {};",
        })
        (self.root / "package-lock.json").write_text('{"lockfileVersion":3}', encoding="utf-8")
        (self.root / "yarn.lock").write_text("# yarn lockfile\n", encoding="utf-8")
        (self.root / "pnpm-lock.yaml").write_text("lockfileVersion: '6.0'\n", encoding="utf-8")
        files = self.bi.walk_repo(self.root)
        names = {f.name for f in files}
        self.assertNotIn("package-lock.json", names)
        self.assertNotIn("yarn.lock", names)
        self.assertNotIn("pnpm-lock.yaml", names)
        self.assertIn("package.json", names)

    def test_excludes_prompt_surface_manifest(self):
        # AC-7 (12cv4): prompt-surface-manifest.json is a machine-generated artifact, not indexed
        _make_repo(self.root, {"docs/prompts/index.md": "# Index\n"})
        manifest = self.root / "docs" / "prompts" / "prompt-surface-manifest.json"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text('{"schema_version":"1.0"}', encoding="utf-8")
        files = self.bi.walk_repo(self.root)
        names = {f.name for f in files}
        self.assertNotIn("prompt-surface-manifest.json", names)
        self.assertIn("index.md", names)

    def test_excludes_snap_keeps_generated_layer_non_vacuous(self):
        # AC-4, AC-5 (12c7n-bug generated-lock-files-indexed): snapshots stay
        # excluded. `.excalidraw` LEFT this layer in wave 1wl7w (1wl7v) — see
        # test_readmits_drawio_and_excalidraw_with_extraction below; `.snap`
        # remains, so the generated-extension layer stays non-vacuous.
        _make_repo(self.root, {"src/foo.ts": "export {};", "src/bar.json": "{}"}),
        (self.root / "src" / "Component.test.ts.snap").write_text("{}", encoding="utf-8")
        files = self.bi.walk_repo(self.root)
        names = {f.name for f in files}
        self.assertNotIn("Component.test.ts.snap", names)
        self.assertIn("foo.ts", names)
        self.assertIn("bar.json", names)
        self.assertIn(".snap", self.bi._GENERATED_EXCLUDE_EXTENSIONS)

    def test_readmits_drawio_and_excalidraw_with_extraction(self):
        # 1wl7v (wave 1wl7w): the executable SUPERSESSION of two shipped
        # exclusions — the 1wl7u census-grounded `.drawio` decision (correct
        # while the file shipped zero rows) and the original `.excalidraw`
        # entry. Label extraction landed (CHUNKER 39), so both extensions walk
        # again WITH retrieval value; WALKER 15 rides the filter-logic clause
        # so consumer indexes re-walk to pick them up.
        _make_repo(self.root, {"docs/readme.md": "# Control\n\nProse.\n"})
        (self.root / "docs" / "pipeline.drawio").write_text(
            '<mxfile host="app.diagrams.net"><diagram id="p" name="Pipeline">'
            '<mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>'
            '<mxCell id="2" value="walker readmission label" vertex="1" parent="1"/>'
            "</root></mxGraphModel></diagram></mxfile>\n",
            encoding="utf-8")
        (self.root / "docs" / "board.excalidraw").write_text(
            '{"type": "excalidraw", "version": 2, "elements": ['
            '{"type": "text", "id": "t1", "isDeleted": false,'
            ' "text": "board label", "originalText": "board label"}],'
            ' "appState": {}, "files": {}}\n',
            encoding="utf-8")
        names = {f.name for f in self.bi.walk_repo(self.root)}
        self.assertIn("pipeline.drawio", names)
        self.assertIn("board.excalidraw", names)
        self.assertIn("readme.md", names)
        self.assertNotIn(".drawio", self.bi._GENERATED_EXCLUDE_EXTENSIONS)
        self.assertNotIn(".excalidraw", self.bi._GENERATED_EXCLUDE_EXTENSIONS)
        self.assertGreaterEqual(int(self.bi.WALKER_VERSION), 15)

    def test_respects_gitignore(self):
        _make_repo(self.root, {
            "src/foo.py": "x = 1\n",
            "build/output.js": "var x = 1;\n",
        })
        (self.root / ".gitignore").write_text("build/\n", encoding="utf-8")
        files = self.bi.walk_repo(self.root)
        self.assertFalse(any("build" in str(f) for f in files))

    def test_respects_aiignore(self):
        _make_repo(self.root, {
            "src/foo.py": "x = 1\n",
            "secret/keys.txt": "token=abc\n",
        })
        (self.root / ".aiignore").write_text("secret/\n", encoding="utf-8")
        files = self.bi.walk_repo(self.root)
        self.assertFalse(any("secret" in str(f) for f in files))

    def test_excludes_wavefoundry_index(self):
        _make_repo(self.root, {"src/foo.py": "x = 1\n"})
        idx = self.root / ".wavefoundry" / "index"
        idx.mkdir(parents=True, exist_ok=True)
        (idx / "docs.json").write_text("[]", encoding="utf-8")
        files = self.bi.walk_repo(self.root)
        self.assertFalse(any(".wavefoundry/index" in str(f).replace("\\", "/") for f in files))

    def test_excludes_wavefoundry_framework_index(self):
        """framework/index/ (pre-built pack index) must never be walked into the project index."""
        _make_repo(self.root, {"src/foo.py": "x = 1\n"})
        fw_idx = self.root / ".wavefoundry" / "framework" / "index"
        fw_idx.mkdir(parents=True, exist_ok=True)
        (fw_idx / "docs.json").write_text("[]", encoding="utf-8")
        files = self.bi.walk_repo(self.root)
        paths = [str(f.relative_to(self.root)).replace("\\", "/") for f in files]
        self.assertFalse(any(p.startswith(".wavefoundry/framework/index/") for p in paths))

    def test_excludes_wavefoundry_runtime_state_files(self):
        _make_repo(self.root, {"src/foo.py": "x = 1\n"})
        (self.root / ".wavefoundry" / "locks" / "dashboard-server.lock").parent.mkdir(parents=True, exist_ok=True)
        (self.root / ".wavefoundry" / "locks" / "dashboard-server.lock").write_text('{"pid": 1}\n', encoding="utf-8")
        (self.root / ".wavefoundry" / "logs").mkdir(parents=True, exist_ok=True)
        (self.root / ".wavefoundry" / "logs" / "dashboard.log").write_text("started\n", encoding="utf-8")
        (self.root / ".wavefoundry" / "guard-overrides.json").write_text('{"seed_edit_allowed": {"enabled": false}}\n', encoding="utf-8")
        files = self.bi.walk_repo(self.root)
        rel_strs = {str(f.relative_to(self.root)).replace("\\", "/") for f in files}
        self.assertNotIn(".wavefoundry/locks/dashboard-server.lock", rel_strs)
        self.assertNotIn(".wavefoundry/logs/dashboard.log", rel_strs)
        self.assertNotIn(".wavefoundry/guard-overrides.json", rel_strs)

    def test_returns_paths_with_forward_slashes(self):
        _make_repo(self.root, {"src/sub/foo.py": "x = 1\n"})
        files = self.bi.walk_repo(self.root)
        for f in files:
            rel = str(f.relative_to(self.root)).replace("\\", "/")
            self.assertNotIn("\\", rel)

    def test_excludes_dot_dirs_blanket(self):
        """All dot-prefix dirs except .wavefoundry are excluded, at any depth."""
        _make_repo(self.root, {"src/foo.py": "x = 1\n"})
        for dot_dir in (".idea", ".vscode", ".cursor", ".claude", ".codex", ".github"):
            d = self.root / dot_dir
            d.mkdir(parents=True, exist_ok=True)
            (d / "settings.json").write_text("{}", encoding="utf-8")
        # Also test nested: a dot-dir inside a non-dot dir
        nested = self.root / "src" / ".idea"
        nested.mkdir(parents=True, exist_ok=True)
        (nested / "workspace.xml").write_text("<project/>", encoding="utf-8")
        files = self.bi.walk_repo(self.root)
        rel_strs = {str(f.relative_to(self.root)).replace("\\", "/") for f in files}
        for dot_dir in (".idea", ".vscode", ".cursor", ".claude", ".codex", ".github"):
            self.assertFalse(
                any(s.startswith(dot_dir + "/") for s in rel_strs),
                f"{dot_dir} should be excluded",
            )
        self.assertNotIn("src/.idea/workspace.xml", rel_strs, "nested .idea should be excluded")

    def test_wavefoundry_dir_still_walked(self):
        """Files under .wavefoundry/ are not excluded by the blanket dot-dir rule."""
        _make_repo(self.root, {
            "src/foo.py": "x = 1\n",
            ".wavefoundry/config.json": '{"ok": true}\n',
        })
        files = self.bi.walk_repo(self.root)
        rel_strs = {str(f.relative_to(self.root)).replace("\\", "/") for f in files}
        self.assertIn(".wavefoundry/config.json", rel_strs)

    def test_includes_env_files_for_scrubbing(self):
        """.env and .env.* files are now included — values are redacted at chunk time."""
        _make_repo(self.root, {"src/foo.py": "x = 1\n"})
        (self.root / ".env").write_text("SECRET=abc\n", encoding="utf-8")
        (self.root / ".env.local").write_text("LOCAL=xyz\n", encoding="utf-8")
        (self.root / ".env.production").write_text("PROD=123\n", encoding="utf-8")
        files = self.bi.walk_repo(self.root)
        names = {f.name for f in files}
        self.assertIn(".env", names)
        self.assertIn(".env.local", names)
        self.assertIn(".env.production", names)

    def test_includes_txt_files(self):
        """.txt files pass through the walker."""
        _make_repo(self.root, {
            "src/foo.py": "x = 1\n",
            "docs/notes.txt": "Some notes.\n",
        })
        files = self.bi.walk_repo(self.root)
        names = {f.name for f in files}
        self.assertIn("notes.txt", names)

    def test_includes_extensionless_readme(self):
        """README and other extensionless docs filenames pass through the walker."""
        _make_repo(self.root, {"src/foo.py": "x = 1\n"})
        for name in ("README", "LICENSE", "CHANGELOG", "CONTRIBUTING", "NOTICE"):
            (self.root / name).write_text(f"# {name}\n", encoding="utf-8")
        files = self.bi.walk_repo(self.root)
        names = {f.name for f in files}
        for name in ("README", "LICENSE", "CHANGELOG", "CONTRIBUTING", "NOTICE"):
            self.assertIn(name, names, f"{name} should be included")

    def test_new_code_extensions_in_source_set(self):
        """AC-7: .xml, .graphql, .gql, .proto, .sql and common SQL aliases are in SOURCE_CODE_EXTENSIONS.
        Plus `.mts`/`.cts` (1p4q4 review B4): TypeScript module extensions are first-class indexable."""
        for ext in (".xml", ".graphql", ".gql", ".proto", ".sql", ".psql", ".pgsql", ".ddl", ".dml", ".tsql", ".hql",
                    ".mts", ".cts"):
            self.assertIn(ext, self.bi.SOURCE_CODE_EXTENSIONS, f"{ext} missing from SOURCE_CODE_EXTENSIONS")


class CodeFileFilterTests(unittest.TestCase):
    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_code_filter_defaults_to_source_files_only(self):
        _make_repo(self.root, {
            "src/foo.py": "def f(): pass\n",
            "src/config.json": "{}\n",
            "docs/guide.md": "# Guide\n\n```python\nprint('example')\n```\n",
            "tests/test_foo.py": "def test_f(): pass\n",
            ".claude/hooks/post-edit.py": "def hook(): pass\n",
            "notes.txt": "not source code\n",
        })

        files = self.bi.walk_repo(self.root)
        filtered = self.bi._filter_code_files(
            files,
            self.root,
            include_tests=False,
            include_generated=False,
        )
        paths = {str(path.relative_to(self.root)).replace("\\", "/") for path in filtered}

        self.assertIn("src/foo.py", paths)
        self.assertIn("src/config.json", paths)
        self.assertNotIn("docs/guide.md", paths)
        self.assertNotIn("tests/test_foo.py", paths)
        self.assertNotIn(".claude/hooks/post-edit.py", paths)
        self.assertNotIn("notes.txt", paths)

    def test_code_filter_can_include_tests_and_generated_files(self):
        # .claude/ is excluded by the blanket dot-dir walker rule, so generated
        # files under .claude/ never reach _filter_code_files regardless of include_generated.
        _make_repo(self.root, {
            "src/foo.py": "def f(): pass\n",
            "tests/test_foo.py": "def test_f(): pass\n",
            "generated/output.py": "def gen(): pass\n",
        })
        # write generated/output.py with a generated-code prefix pattern via a non-dot dir
        (self.root / "generated" / "output.py").write_text("def gen(): pass\n", encoding="utf-8")

        files = self.bi.walk_repo(self.root)
        filtered = self.bi._filter_code_files(
            files,
            self.root,
            include_tests=True,
            include_generated=True,
        )
        paths = {str(path.relative_to(self.root)).replace("\\", "/") for path in filtered}

        self.assertIn("src/foo.py", paths)
        self.assertIn("tests/test_foo.py", paths)

    def test_code_filter_always_excludes_framework_internal_tests(self):
        _make_repo(self.root, {
            ".wavefoundry/framework/scripts/indexer.py": "def build_index(): pass\n",
            ".wavefoundry/framework/scripts/tests/test_indexer.py": "def test_build_index(): pass\n",
        })

        files = self.bi.walk_repo(self.root)
        filtered = self.bi._filter_code_files(
            files,
            self.root,
            include_tests=True,
            include_generated=True,
        )
        paths = {str(path.relative_to(self.root)).replace("\\", "/") for path in filtered}

        self.assertIn(".wavefoundry/framework/scripts/indexer.py", paths)
        self.assertNotIn(".wavefoundry/framework/scripts/tests/test_indexer.py", paths)

    def test_framework_pack_artifacts_filter_strips_transient_extensions(self):
        """Regression for 130o2: transient artifact extensions must be stripped from
        the framework-layer walk so they never enter framework meta.json or the pack."""
        _make_repo(self.root, {
            ".wavefoundry/framework/scripts/tool.py": "def t(): pass\n",
            ".wavefoundry/framework/test-run.lock": "pid\n",
            ".wavefoundry/framework/index/index-build.lock": "pid\n",
            ".wavefoundry/framework/index/index-build.log": "log line\n",
            ".wavefoundry/framework/index/index-build-docs.log": "log line\n",
            ".wavefoundry/framework/leftover.bak": "editor backup\n",
            ".wavefoundry/framework/leftover.swp": "editor swap\n",
            ".wavefoundry/framework/leftover.tmp": "temp\n",
            ".wavefoundry/framework/conflict.orig": "merge artifact\n",
            ".wavefoundry/framework/conflict.rej": "merge artifact\n",
        })
        files = self.bi.walk_repo(self.root, respect_ignore=False)
        framework_files = [
            p for p in files
            if str(p.relative_to(self.root)).replace("\\", "/").startswith(".wavefoundry/framework/")
        ]
        filtered = self.bi._filter_framework_pack_artifacts(framework_files, self.root)
        paths = {str(p.relative_to(self.root)).replace("\\", "/") for p in filtered}

        # Source files survive
        self.assertIn(".wavefoundry/framework/scripts/tool.py", paths)
        # Every transient extension stripped
        for forbidden in [
            ".wavefoundry/framework/test-run.lock",
            ".wavefoundry/framework/index/index-build.lock",
            ".wavefoundry/framework/index/index-build.log",
            ".wavefoundry/framework/index/index-build-docs.log",
            ".wavefoundry/framework/leftover.bak",
            ".wavefoundry/framework/leftover.swp",
            ".wavefoundry/framework/leftover.tmp",
            ".wavefoundry/framework/conflict.orig",
            ".wavefoundry/framework/conflict.rej",
        ]:
            self.assertNotIn(forbidden, paths, f"transient artifact leaked: {forbidden}")


class HashTests(unittest.TestCase):
    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_same_content_same_hash(self):
        p = self.root / "f.py"
        p.write_text("x = 1\n", encoding="utf-8")
        h1 = self.bi._sha256(p)
        h2 = self.bi._sha256(p)
        self.assertEqual(h1, h2)

    def test_different_content_different_hash(self):
        p = self.root / "f.py"
        p.write_text("x = 1\n", encoding="utf-8")
        h1 = self.bi._sha256(p)
        p.write_text("x = 2\n", encoding="utf-8")
        h2 = self.bi._sha256(p)
        self.assertNotEqual(h1, h2)

    def test_build_file_hashes_returns_rel_path_to_hex(self):
        (self.root / "a.py").write_text("hello\n", encoding="utf-8")
        (self.root / "sub").mkdir()
        (self.root / "sub" / "b.md").write_text("world\n", encoding="utf-8")
        files = [self.root / "a.py", self.root / "sub" / "b.md"]
        result = self.bi._build_file_hashes(files, self.root)
        self.assertEqual(set(result.keys()), {"a.py", "sub/b.md"})
        for v in result.values():
            self.assertRegex(v, r"^[0-9a-f]{64}$")

    def test_build_file_hashes_consistent_with_sha256(self):
        p = self.root / "c.py"
        p.write_text("data\n", encoding="utf-8")
        result = self.bi._build_file_hashes([p], self.root)
        self.assertEqual(result["c.py"], self.bi._sha256(p))


class ProjectIndexInputsStaleTests(unittest.TestCase):
    """Wave 1p5xu: indexer.project_index_inputs_stale cheap stat-fast-path check."""

    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root, {"docs/guide.md": "# Guide\n\nOriginal.\n"})
        self.index_dir = self.root / ".wavefoundry" / "index"
        self.index_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _build_meta(self) -> dict:
        """Compute a current file_meta snapshot using the indexer's own primitives."""
        files = self.bi.walk_repo(self.root, respect_ignore=True)
        files = [p for p in files if not self.bi._is_relative_to(p, self.index_dir)]
        files = self.bi._filter_project_index_excludes(
            files, self.root, (),
            project_include_prefixes=self.bi.FRAMEWORK_FOLD_DOCS_PREFIXES,
        )
        current, _, _ = self.bi._detect_changes(files, self.root, {})
        return {"built_at": "2026-06-16T00:00:00Z", "file_meta": current}

    def test_returns_none_when_no_file_meta(self):
        self.assertIsNone(self.bi.project_index_inputs_stale(self.root, {}))
        self.assertIsNone(self.bi.project_index_inputs_stale(self.root, {"file_meta": {}}))

    def test_returns_false_when_inputs_unchanged(self):
        meta = self._build_meta()
        self.assertFalse(self.bi.project_index_inputs_stale(self.root, meta))

    def test_returns_true_when_file_content_changes(self):
        meta = self._build_meta()
        (self.root / "docs" / "guide.md").write_text("# Guide\n\nChanged.\n", encoding="utf-8")
        self.assertTrue(self.bi.project_index_inputs_stale(self.root, meta))

    def test_generated_codebase_map_does_not_drive_staleness(self):
        # Wave 1p601: writing the generated codebase map through create-mode lifecycle,
        # upgrade, map-only/CLI, or missing-file resource paths must NOT mark the index stale — otherwise it would trigger
        # a reindex (the write→reindex coupling the decoupling eliminates).
        meta = self._build_meta()
        map_path = self.root / "docs" / "references" / "codebase-map.md"
        map_path.parent.mkdir(parents=True, exist_ok=True)
        map_path.write_text("# Codebase Map\n\nbrand new generated content\n", encoding="utf-8")
        self.assertFalse(self.bi.project_index_inputs_stale(self.root, meta))

    def test_returns_true_when_indexed_file_removed(self):
        meta = self._build_meta()
        (self.root / "docs" / "guide.md").unlink()
        self.assertTrue(self.bi.project_index_inputs_stale(self.root, meta))

    def test_loads_meta_from_disk_when_not_passed(self):
        meta = self._build_meta()
        _seed_meta_store(self.index_dir, meta)
        self.assertFalse(self.bi.project_index_inputs_stale(self.root))
        (self.root / "docs" / "guide.md").write_text("# Guide\n\nChanged.\n", encoding="utf-8")
        self.assertTrue(self.bi.project_index_inputs_stale(self.root))


class IndexBuildLockTests(unittest.TestCase):
    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root, {"docs/guide.md": "# Guide\n"})
        self.index_dir = self.root / ".wavefoundry" / "index"
        self.index_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_index_build_lock_leaves_metadata_but_releases_os_lock(self):
        lock_path = self.index_dir / self.bi.INDEX_BUILD_LOCK_NAME

        with self.bi._index_build_lock(self.index_dir):
            self.assertTrue(lock_path.exists())
            data = json.loads(lock_path.read_text(encoding="utf-8"))
            self.assertEqual(data.get("pid"), os.getpid())
            self.assertIsInstance(data.get("started_at"), float)

        with self.bi._index_build_lock(self.index_dir):
            self.assertTrue(lock_path.exists())

    def test_main_fails_fast_when_another_process_holds_index_lock(self):
        holder = textwrap.dedent(
            f"""
            import importlib.util
            import pathlib
            import sys
            import time

            spec = importlib.util.spec_from_file_location("indexer_holder", {str(INDEXER_PATH)!r})
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            with mod._index_build_lock(pathlib.Path(sys.argv[1])):
                print("locked", flush=True)
                time.sleep(2.0)
            """
        )

        proc = subprocess.Popen(
            [sys.executable, "-B", "-c", holder, str(self.index_dir)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            self.assertEqual(proc.stdout.readline().strip(), "locked")
            rc = self.bi.main([
                "--root", str(self.root),
                "--index-dir", str(self.index_dir),
                "--content", "docs",
            ])
            self.assertEqual(rc, 1)
        finally:
            proc.terminate()
            proc.communicate(timeout=5)

    def test_stale_lock_metadata_is_reclaimed_on_acquire(self):
        lock_path = self.index_dir / self.bi.INDEX_BUILD_LOCK_NAME
        lock_path.write_text(
            json.dumps({"pid": 99999999, "started_at": 0.0}),
            encoding="utf-8",
        )
        err_buf = io.StringIO()
        with redirect_stderr(err_buf):
            with self.bi._index_build_lock(self.index_dir):
                data = json.loads(lock_path.read_text(encoding="utf-8"))
                self.assertEqual(data.get("pid"), os.getpid())
        self.assertIn("reclaimed stale", err_buf.getvalue())

    def test_classify_index_build_lock_owner_live_and_stale(self):
        # Wave 1p98u: a live owner is a running index-builder process (not merely os.kill-alive).
        with patch.object(self.bi, "_pid_is_index_builder", return_value=True):
            live = self.bi.classify_index_build_lock_owner(
                {"pid": os.getpid(), "started_at": time.time()}
            )
        self.assertEqual(live, "live")
        stale = self.bi.classify_index_build_lock_owner(
            {"pid": 99999999, "started_at": 0.0}
        )
        self.assertEqual(stale, "stale")
        completed = self.bi.classify_index_build_lock_owner(
            {"pid": 99999999, "started_at": time.time()}
        )
        self.assertEqual(completed, "completed")

    def test_stale_lock_file_is_unlinked_before_acquire(self):
        """Wave 1p2q3 (1p2w5 / Bug 1): a lock file whose metadata records a
        dead PID must be unlinked at `_index_build_lock` entry so downstream
        tools that read the file (status surfaces, diagnostic messages) see
        the fresh post-acquire metadata, not the dead-pid legacy."""
        lock_path = self.index_dir / self.bi.INDEX_BUILD_LOCK_NAME
        lock_path.write_text(
            json.dumps({"pid": 99999999, "started_at": 0.0}),
            encoding="utf-8",
        )
        # Capture the inode of the pre-existing file so we can confirm the
        # post-acquire file is a fresh inode (i.e. the unlink ran).
        pre_inode = lock_path.stat().st_ino
        with redirect_stderr(io.StringIO()):
            with self.bi._index_build_lock(self.index_dir):
                post_inode = lock_path.stat().st_ino
                meta = json.loads(lock_path.read_text(encoding="utf-8"))
                self.assertEqual(meta.get("pid"), os.getpid())
        self.assertNotEqual(
            pre_inode, post_inode,
            "stale lock file should have been unlinked before acquire — "
            "same inode means the original dead-PID metadata file was reused",
        )

    def test_recent_completed_owner_does_not_log_reclaimed_stale(self):
        lock_path = self.index_dir / self.bi.INDEX_BUILD_LOCK_NAME
        lock_path.write_text(
            json.dumps({"pid": 99999999, "started_at": time.time()}),
            encoding="utf-8",
        )
        err_buf = io.StringIO()
        with redirect_stderr(err_buf):
            with self.bi._index_build_lock(self.index_dir):
                pass
        self.assertNotIn("reclaimed stale", err_buf.getvalue())

    def test_format_index_build_lock_conflict_distinguishes_live_and_stale(self):
        (self.index_dir / self.bi.INDEX_BUILD_LOCK_NAME).write_text(
            json.dumps({"pid": os.getpid(), "started_at": time.time()}),
            encoding="utf-8",
        )
        with patch.object(self.bi, "_pid_is_index_builder", return_value=True):
            live_msg = self.bi.format_index_build_lock_conflict(self.index_dir)
        self.assertIn("live build in progress", live_msg)

        (self.index_dir / self.bi.INDEX_BUILD_LOCK_NAME).write_text(
            json.dumps({"pid": 99999999, "started_at": 0.0}),
            encoding="utf-8",
        )
        stale_msg = self.bi.format_index_build_lock_conflict(self.index_dir)
        self.assertIn("appears stale", stale_msg)

    def test_should_coalesce_hook_reindex_when_live_or_recent_spawn(self):
        lock_path = self.index_dir / self.bi.INDEX_BUILD_LOCK_NAME
        lock_path.write_text(
            json.dumps({"pid": os.getpid(), "started_at": time.time()}),
            encoding="utf-8",
        )
        # Wave 1p98u: the live-owner coalesce path requires the owner be a running index builder.
        with patch.object(self.bi, "_pid_is_index_builder", return_value=True):
            self.assertTrue(self.bi.should_coalesce_hook_reindex(self.index_dir))

        lock_path.write_text(
            json.dumps({"pid": 99999999, "started_at": 0.0}),
            encoding="utf-8",
        )
        self.bi.record_hook_reindex_spawn(self.index_dir)
        self.assertTrue(self.bi.should_coalesce_hook_reindex(self.index_dir))

        # Wave 1p9am: the debounce is now 45s — backdate the last-spawn marker past the window rather
        # than sleeping it out.
        (self.index_dir / self.bi.HOOK_REINDEX_LAST_SPAWN_NAME).write_text(
            str(time.time() - self.bi.HOOK_REINDEX_DEBOUNCE_SECONDS - 1.0), encoding="utf-8"
        )
        self.assertFalse(self.bi.should_coalesce_hook_reindex(self.index_dir))

    # ---- Wave 1p98u: zombie / recycled-PID liveness hardening ----

    def test_zombie_owner_reads_not_running(self):
        # A defunct owner (os.kill-alive but Z-state) must read as not running.
        with patch.object(self.bi, "_process_is_zombie", return_value=True):
            self.assertFalse(self.bi._pid_is_running(os.getpid()))

    def test_zombie_owner_classifies_stale_and_reclaims(self):
        # A zombie owner → not live → age-based stale → the existing reclaim path clears it.
        lock_path = self.index_dir / self.bi.INDEX_BUILD_LOCK_NAME
        lock_path.write_text(
            json.dumps({"pid": os.getpid(), "started_at": 0.0}), encoding="utf-8"
        )
        with patch.object(self.bi, "_process_is_zombie", return_value=True):
            owner = self.bi.classify_index_build_lock_owner(
                self.bi.read_index_build_lock_metadata(lock_path)
            )
            self.assertEqual(owner, "stale")
            with redirect_stderr(io.StringIO()):
                with self.bi._index_build_lock(self.index_dir):
                    data = json.loads(lock_path.read_text(encoding="utf-8"))
                    self.assertEqual(data.get("pid"), os.getpid())

    def test_recycled_pid_not_index_builder_is_not_live(self):
        # A live PID whose cmdline is not an index build (recycled PID) must not read as a live build.
        with patch.object(self.bi, "_process_cmdline", return_value="/bin/bash -l"):
            recent = self.bi.classify_index_build_lock_owner(
                {"pid": os.getpid(), "started_at": time.time()}
            )
            self.assertEqual(recent, "completed")  # not live
            old = self.bi.classify_index_build_lock_owner(
                {"pid": os.getpid(), "started_at": 0.0}
            )
            self.assertEqual(old, "stale")

    def test_live_index_builder_classifies_live(self):
        with patch.object(
            self.bi, "_process_cmdline",
            return_value="python3 .wavefoundry/framework/scripts/indexer.py --root .",
        ):
            self.assertEqual(
                self.bi.classify_index_build_lock_owner(
                    {"pid": os.getpid(), "started_at": time.time()}
                ),
                "live",
            )

    def test_scan_unavailable_owner_treated_live_not_reclaimed(self):
        # When the cmdline scan is unavailable, an alive owner stays "live" (never reclaimed → no
        # double-build); the OS flock remains the authority.
        with patch.object(self.bi, "_process_cmdline", return_value=None):
            self.assertEqual(
                self.bi.classify_index_build_lock_owner(
                    {"pid": os.getpid(), "started_at": time.time()}
                ),
                "live",
            )

    def test_metadata_without_cmdline_marker_degrades_gracefully(self):
        # Older metadata lacking the "cmdline" field must classify without crashing (liveness uses
        # the live PID's cmdline, not the recorded marker).
        with patch.object(self.bi, "_process_cmdline", return_value=None):
            owner = self.bi.classify_index_build_lock_owner(
                {"pid": os.getpid(), "started_at": time.time()}
            )
        self.assertEqual(owner, "live")

    def test_lock_metadata_records_cmdline_marker(self):
        lock_path = self.index_dir / self.bi.INDEX_BUILD_LOCK_NAME
        with self.bi._index_build_lock(self.index_dir):
            data = json.loads(lock_path.read_text(encoding="utf-8"))
        self.assertIn("cmdline", data)
        self.assertIsInstance(data["cmdline"], str)

    def test_process_is_zombie_parses_ps_state(self):
        def fake_run(cmd, **kw):
            return MagicMock(returncode=0, stdout="Z\n")
        with patch.object(self.bi, "os") as fake_os:
            fake_os.name = "posix"
            with patch.object(self.bi.subprocess_util, "isolated_run", side_effect=fake_run):
                self.assertTrue(self.bi._process_is_zombie(4321))
        with patch.object(self.bi, "os") as fake_os:
            fake_os.name = "posix"
            with patch.object(self.bi.subprocess_util, "isolated_run",
                              side_effect=lambda cmd, **kw: MagicMock(returncode=0, stdout="S\n")):
                self.assertFalse(self.bi._process_is_zombie(4321))

    def test_process_is_zombie_noop_on_windows(self):
        with patch.object(self.bi, "os") as fake_os:
            fake_os.name = "nt"
            with patch.object(self.bi.subprocess_util, "isolated_run") as run:
                self.assertFalse(self.bi._process_is_zombie(4321))
                run.assert_not_called()

    def test_liveness_probes_route_through_windowless_helper(self):
        # AC-6: process probes must use subprocess_util.isolated_run (windowless), never bare subprocess.
        captured = {}
        def fake_run(cmd, **kw):
            captured["cmd"] = cmd
            return MagicMock(returncode=0, stdout="python indexer.py --root .")
        with patch.object(self.bi.subprocess_util, "isolated_run", side_effect=fake_run):
            self.bi._process_cmdline(4321)
        self.assertIn("cmd", captured)


class IncrementalBuildTests(unittest.TestCase):
    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _run_build(self, full: bool = False) -> dict:
        docs_mock = _make_embedder_mock(dim=4)
        code_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", side_effect=[docs_mock, code_mock]):
            return self.bi.build_index(self.root, full=full, content="all", verbose=False)

    def test_full_build_produces_index_files(self):
        _make_repo(self.root, {
            "src/foo.py": "def f(): pass\n",
            "docs/guide.md": "## Intro\n\nHello.\n",
        })
        result = self._run_build(full=True)
        index_dir = self.root / ".wavefoundry" / "index"
        # 1sed6: SQLite is the only state authority — no meta.json is written.
        self.assertFalse((index_dir / "meta.json").exists())
        self.assertTrue(_read_meta_store(index_dir).get("file_meta"))
        has_index = (index_paths.runtime_database_path(index_dir)).is_file()
        self.assertTrue(has_index)
        self.assertFalse(result["up_to_date"])

    def test_build_accepts_device_drift_without_restamping_receipt(self):
        import sqlite_storage_migration as migration
        _make_repo(self.root, {"docs/guide.md": "## Before\n\nOriginal text.\n"})
        self._run_build(full=True)
        index_dir = self.root / ".wavefoundry" / "index"
        # Production producer supplies the old-format identity shape. The
        # completed status models a standing receipt, not an active migration.
        receipt = migration._new_receipt(None, self.root, index_dir, migration.detect(index_dir))
        receipt["state"] = "complete"
        migration._write(index_dir, receipt)
        receipt_path = index_dir / migration.RECEIPT
        before = receipt_path.read_bytes()
        identity = migration._identity
        def drift(path):
            value = identity(path)
            return {**value, "device": value["device"] + 1}
        (self.root / "docs/guide.md").write_text("## After\n\nChanged text.\n")
        with patch.object(migration, "_identity", side_effect=drift):
            result = self._run_build()
            self.assertFalse(result.get("failed"), result.get("failure"))
            self.assertEqual(receipt, migration.read_receipt(index_dir))
        self.assertFalse(result["up_to_date"])
        self.assertTrue(_read_meta_store(index_dir).get("file_meta"))
        self.assertEqual(before, receipt_path.read_bytes())

    def test_explicit_initial_build_excludes_ledger_but_indexes_projection_and_same_name(self):
        """The caller-supplied files= seam cannot bypass the canonical-ledger boundary."""
        canonical = "docs/waves/1slep external-ledger/events.jsonl"
        projection = "docs/waves/1slep external-ledger/wave.md"
        unrelated = "audit/events.jsonl"
        # FU4: folder spelling no longer decides the wave-folder role, so a
        # ledger directly under ANY docs/waves child is excluded. The control
        # for "not the canonical authority, still searchable" is now DEPTH.
        unrelated_wave_note = "docs/waves/notes/attachments/events.jsonl"
        _make_repo(self.root, {
            canonical: '{"finding":"superseded raw history"}\n',
            # component-fixture: test_explicit_initial_build_excludes_ledger_but_indexes_projection_and_same_name exercises this input representation directly
            projection: "# Wave\nreview-evidence-source: events.jsonl\n\n# Current findings\n\nSearchable head.\n",
            unrelated: '{"audit":"searchable"}\n',
            unrelated_wave_note: '{"note":"searchable"}\n',
            "docs/waves/notes/wave.md": "# Design notes, not a Wavefoundry wave\n",
        })

        docs_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", return_value=docs_mock):
            self.bi.build_index(
                self.root,
                full=False,
                content="docs",
                files=[
                    self.root / canonical,
                    self.root / projection,
                    self.root / unrelated,
                    self.root / unrelated_wave_note,
                ],
                verbose=False,
            )

        index_dir = self.root / ".wavefoundry" / "index"
        meta_paths = set((_read_meta_store(index_dir).get("file_meta") or {}).keys())
        chunk_paths = {row["path"] for row in _read_index_chunks(index_dir, "docs")}
        self.assertNotIn(canonical, meta_paths)
        self.assertNotIn(canonical, chunk_paths)
        self.assertIn(projection, meta_paths)
        self.assertIn(projection, chunk_paths)
        self.assertIn(unrelated, meta_paths)
        self.assertIn(unrelated_wave_note, meta_paths)

    def test_explicit_initial_build_excludes_archive_bodies_and_legacy_pointers(self):
        """Caller-supplied files cannot bypass either memory-history boundary."""
        archive = "docs/agents/memory/archive/mem-old.md"
        legacy_pointer = "docs/agents/memory/pointers/mem-old.md"
        register = "docs/agents/memory-archive.md"
        _make_repo(self.root, {
            archive: "# Archived full body\n",
            legacy_pointer: "# Retired generated pointer\n",
            register: "# Memory archive\n\n## mem-old\n",
        })

        docs_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", return_value=docs_mock):
            self.bi.build_index(
                self.root,
                full=False,
                content="docs",
                files=[
                    self.root / archive,
                    self.root / legacy_pointer,
                    self.root / register,
                ],
                verbose=False,
            )

        index_dir = self.root / ".wavefoundry" / "index"
        meta_paths = set((_read_meta_store(index_dir).get("file_meta") or {}).keys())
        chunk_paths = {row["path"] for row in _read_index_chunks(index_dir, "docs")}
        self.assertNotIn(archive, meta_paths)
        self.assertNotIn(archive, chunk_paths)
        self.assertNotIn(legacy_pointer, meta_paths)
        self.assertNotIn(legacy_pointer, chunk_paths)
        self.assertIn(register, meta_paths)
        self.assertIn(register, chunk_paths)

    def test_incremental_exclusion_reaps_previously_indexed_canonical_ledger(self):
        """A pre-cutover row becomes a removal and is evicted from metadata and Lance."""
        canonical = "docs/waves/1slep external-ledger/events.jsonl"
        projection = "docs/waves/1slep external-ledger/wave.md"
        unrelated = "audit/events.jsonl"
        # FU4: folder spelling no longer decides the wave-folder role, so a
        # ledger directly under ANY docs/waves child is excluded. The control
        # for "not the canonical authority, still searchable" is now DEPTH.
        unrelated_wave_note = "docs/waves/notes/attachments/events.jsonl"
        _make_repo(self.root, {
            canonical: '{"finding":"old indexed authority"}\n',
            # component-fixture: test_incremental_exclusion_reaps_previously_indexed_canonical_ledger exercises this input representation directly
            projection: "# Wave\nreview-evidence-source: events.jsonl\n\n# Current findings\n\nSearchable head.\n",
            unrelated: '{"audit":"still searchable"}\n',
            unrelated_wave_note: '{"note":"still searchable"}\n',
            "docs/waves/notes/wave.md": "# Design notes, not a Wavefoundry wave\n",
        })

        # Simulate a prior build that admitted and emitted a docs row for the
        # ledger.  The chunk override makes the stale-row fixture non-vacuous
        # even though current generic .jsonl dispatch produces a code-kind
        # line window that is not part of the source-code corpus.
        original_chunks_for_file = self.bi._chunks_for_file

        def legacy_chunks_for_file(rel_path, content):
            if rel_path == canonical:
                return ([{
                    "id": f"{canonical}::legacy-ledger-row",
                    "path": canonical,
                    "kind": "doc",
                    "language": None,
                    "lines": [1, 1],
                    "section": "events",
                    "text": content,
                }], [])
            return original_chunks_for_file(rel_path, content)

        with (
            patch.object(self.bi, "_is_canonical_wave_events_path", return_value=False),
            patch.object(self.bi, "_chunks_for_file", side_effect=legacy_chunks_for_file),
        ):
            self._run_build(full=True)
        index_dir = self.root / ".wavefoundry" / "index"
        before_meta = set((_read_meta_store(index_dir).get("file_meta") or {}).keys())
        before_chunks = {row["path"] for row in _read_index_chunks(index_dir, "docs")}
        self.assertIn(canonical, before_meta, "fixture must prove the old walker admitted the ledger")
        self.assertIn(canonical, before_chunks, "fixture must seed a real stale semantic row")

        docs_mock = _make_embedder_mock(dim=4)
        code_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", side_effect=[docs_mock, code_mock]):
            result = self.bi.build_index(self.root, full=False, content="all", verbose=False)

        after_meta = set((_read_meta_store(index_dir).get("file_meta") or {}).keys())
        after_chunks = {row["path"] for row in _read_index_chunks(index_dir, "docs")}
        self.assertFalse(result["up_to_date"])
        self.assertNotIn(canonical, after_meta)
        self.assertNotIn(canonical, after_chunks)
        self.assertIn(projection, after_meta)
        self.assertIn(projection, after_chunks)
        self.assertIn(unrelated, after_meta)
        self.assertIn(unrelated_wave_note, after_meta)

    def test_incremental_exclusion_reaps_previously_indexed_graphify_output(self):
        """The default Graphify output is removed without a full index rebuild."""
        graphify_output = "graphify-out/GRAPH_REPORT.md"
        source_control = "src/graphify-output.ts"
        _make_repo(self.root, {
            graphify_output: "# Generated Graphify report\n",
            source_control: "export const source = true;\n",
        })

        old_excludes = self.bi.HARDCODED_EXCLUDE_DIRS - {"graphify-out"}
        with patch.object(self.bi, "HARDCODED_EXCLUDE_DIRS", old_excludes):
            self._run_build(full=True)

        index_dir = self.root / ".wavefoundry" / "index"
        before_meta = set((_read_meta_store(index_dir).get("file_meta") or {}).keys())
        import index_state_store

        def _graph_paths():
            conn = index_state_store.open_read_only(index_dir)
            try:
                return {str(row[0]) for row in conn.execute("SELECT path FROM graph_file_state")}
            finally:
                conn.close()

        before_graph_paths = _graph_paths()
        self.assertIn(graphify_output, before_meta, "fixture must seed an old indexed Graphify file")
        self.assertIn(graphify_output, before_graph_paths, "fixture must seed an old graph file")

        result = self._run_build(full=False)

        after_meta = set((_read_meta_store(index_dir).get("file_meta") or {}).keys())
        doc_paths = {row["path"] for row in _read_index_chunks(index_dir, "docs")}
        after_graph_paths = _graph_paths()
        self.assertFalse(result["up_to_date"])
        self.assertNotIn(graphify_output, after_meta)
        self.assertNotIn(graphify_output, doc_paths)
        self.assertNotIn(graphify_output, after_graph_paths)
        self.assertIn(source_control, after_meta)
        self.assertIn(source_control, after_graph_paths)

    def test_incremental_ledger_add_modify_delete_are_semantic_noops(self):
        """Canonical machine-state churn never enters incremental docs/code state."""
        canonical = self.root / "docs/waves/1slep external-ledger/events.jsonl"
        _make_repo(self.root, {
            # component-fixture: test_incremental_ledger_add_modify_delete_are_semantic_noops exercises this input representation directly
            "docs/waves/1slep external-ledger/wave.md": "# Wave\nreview-evidence-source: events.jsonl\n\n# Searchable current head\n",
            "src/app.py": "def app():\n    return 1\n",
        })
        self._run_build(full=True)

        canonical.parent.mkdir(parents=True, exist_ok=True)
        canonical.write_text('{"event":1}\n', encoding="utf-8")
        added = self.bi.build_index(self.root, full=False, content="all", verbose=False)
        canonical.write_text('{"event":2}\n', encoding="utf-8")
        modified = self.bi.build_index(self.root, full=False, content="all", verbose=False)
        canonical.unlink()
        deleted = self.bi.build_index(self.root, full=False, content="all", verbose=False)

        for result in (added, modified, deleted):
            self.assertTrue(result["up_to_date"])
            self.assertEqual(result["files_indexed"], 0)
        index_dir = self.root / ".wavefoundry" / "index"
        meta_paths = set((_read_meta_store(index_dir).get("file_meta") or {}).keys())
        docs_paths = {row["path"] for row in _read_index_chunks(index_dir, "docs")}
        code_paths = {row["path"] for row in _read_index_chunks(index_dir, "code")}
        rel = "docs/waves/1slep external-ledger/events.jsonl"
        self.assertNotIn(rel, meta_paths)
        self.assertNotIn(rel, docs_paths)
        self.assertNotIn(rel, code_paths)

    def test_build_does_not_write_codebase_map(self):
        # Wave 1p601 AC-2b: map regen is DECOUPLED from the index build — an
        # indexer-driven build must NOT write docs/references/codebase-map.md
        # (that would create a write→reindex loop into the indexed docs tree).
        _make_repo(self.root, {
            "src/foo.py": "def f(): pass\n",
            "docs/guide.md": "## Intro\n\nHello.\n",
        })
        self._run_build(full=True)
        map_path = self.root / "docs" / "references" / "codebase-map.md"
        self.assertFalse(map_path.exists(), "indexer build must NOT regenerate the codebase map")

    def test_second_run_is_up_to_date(self):
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        self._run_build(full=True)
        # Next run — no changes, no embedder calls needed; a true no-op.
        result = self.bi.build_index(self.root, full=False, content="all", verbose=False)
        self.assertTrue(result["up_to_date"])
        self.assertEqual(result["files_indexed"], 0)

    def test_incremental_docs_only_change_skips_code_embedder(self):
        """1p5d6: an incremental update touching only a doc file must NOT construct the code
        embedder (no new code chunks → no model load)."""
        _make_repo(self.root, {
            "src/foo.py": "def f():\n    return 1\n",
            "docs/guide.md": "## Intro\n\nHello.\n",
        })
        self._run_build(full=True)
        (self.root / "docs" / "guide.md").write_text("## Intro\n\nHello changed now.\n", encoding="utf-8")
        requested: list[tuple[str, int | None]] = []

        def spy(model, n_chunks=None):
            requested.append((model, n_chunks))
            return _make_embedder_mock(dim=4)

        with patch.object(self.bi, "_get_embedder", side_effect=spy):
            self.bi.build_index(self.root, full=False, content="all", verbose=False)
        self.assertEqual(len(requested), 1, "a docs-only change must resolve exactly one embedder")
        self.assertEqual(requested[0][0], self.bi.DOCS_MODEL)
        self.assertGreater(requested[0][1] or 0, 0)

    def test_incremental_code_only_change_skips_docs_embedder(self):
        """1p5d6: the mirror — a code-only change must not construct the docs embedder."""
        _make_repo(self.root, {
            "src/foo.py": "def f():\n    return 1\n",
            "docs/guide.md": "## Intro\n\nHello.\n",
        })
        self._run_build(full=True)
        (self.root / "src" / "foo.py").write_text("def f():\n    return 42\n", encoding="utf-8")
        requested: list[tuple[str, int | None]] = []

        def spy(model, n_chunks=None):
            requested.append((model, n_chunks))
            return _make_embedder_mock(dim=4)

        with patch.object(self.bi, "_get_embedder", side_effect=spy):
            self.bi.build_index(self.root, full=False, content="all", verbose=False)
        self.assertEqual(len(requested), 1, "a code-only change must resolve exactly one embedder")
        self.assertEqual(requested[0][0], self.bi.CODE_MODEL)
        self.assertGreater(requested[0][1] or 0, 0)

    def test_full_rebuild_loads_both_embedders(self):
        """1p5d6: a full rebuild always loads both layer embedders (both layers have all chunks)."""
        _make_repo(self.root, {
            "src/foo.py": "def f():\n    return 1\n",
            "docs/guide.md": "## Intro\n\nHello.\n",
        })
        requested: list[str] = []

        def spy(model, n_chunks=None):
            requested.append(model)
            return _make_embedder_mock(dim=4)

        with patch.object(self.bi, "_get_embedder", side_effect=spy):
            self.bi.build_index(self.root, full=True, content="all", verbose=False)
        self.assertEqual(requested, [self.bi.DOCS_MODEL])

    def test_chunker_version_bump_reuses_vectors_no_reembed(self):
        """1p4n4: a chunker-ONLY version bump re-chunks every file but reuses embeddings by
        content hash — content-identical chunks are NOT re-embedded (no full re-encode)."""
        _make_repo(self.root, {"src/foo.py": "def f():\n    return 1\n\ndef g():\n    return 2\n"})
        self._run_build(full=True)
        index_dir = self.root / ".wavefoundry" / "index"
        meta = _read_meta_store(index_dir)
        meta.setdefault("chunker_versions", {})["code"] = "0"  # simulate a bump
        _seed_meta_store(index_dir, meta)

        code_calls: list[list[str]] = []
        spy = _make_embedder_mock(dim=4, calls=code_calls)
        with patch.object(self.bi, "_get_embedder", return_value=spy):
            self.bi.build_index(self.root, full=False, content="code", verbose=False)

        embedded = [t for batch in code_calls for t in batch]
        self.assertEqual(embedded, [], "chunker-only bump must reuse vectors, not re-embed")
        # the bump is recorded (so it doesn't re-trigger)
        meta2 = _read_meta_store(index_dir)
        self.assertEqual(meta2["chunker_versions"]["code"], self.bi._get_chunker().CHUNKER_VERSION)

    def test_model_version_bump_reembeds_all_no_reuse(self):
        """1p4n4: a MODEL-version change forces a full re-embed (old-model vectors are invalid)
        — it must NOT take the chunker-only reuse path."""
        _make_repo(self.root, {"src/foo.py": "def f():\n    return 1\n"})
        self._run_build(full=True)
        index_dir = self.root / ".wavefoundry" / "index"
        meta = _read_meta_store(index_dir)
        meta.setdefault("model_versions", {})["code"] = "old-model"
        _seed_meta_store(index_dir, meta)

        code_calls: list[list[str]] = []
        spy = _make_embedder_mock(dim=4, calls=code_calls)
        with patch.object(self.bi, "_get_embedder", return_value=spy):
            self.bi.build_index(self.root, full=False, content="code", verbose=False)

        embedded = [t for batch in code_calls for t in batch]
        self.assertTrue(any("return 1" in t for t in embedded), "model change must re-embed, not reuse")

    def test_framework_seeds_and_readme_fold_into_project_docs_index(self):
        """1p4ww (real-pipeline regression): the framework seeds + README must actually
        land in the project docs index. The original fold unit tests wrote synthetic index
        rows and never exercised the walk+filter pipeline, which dropped the seeds at the
        ``files_for_meta`` stage (it used the docs+code graph surface, not the fold prefixes)."""
        _make_repo(self.root, {
            "docs/guide.md": "## Intro\n\nProject docs.\n",
            ".wavefoundry/framework/seeds/100-install.prompt.md": "# Install seed\n\nHow to install.\n",
            ".wavefoundry/framework/README.md": "# Wavefoundry Framework\n\nOverview.\n",
        })
        docs_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", side_effect=[docs_mock]):
            self.bi.build_index(self.root, full=True, content="docs", verbose=False)

        import lancedb
        rows = _read_index_chunks(self.root / ".wavefoundry" / "index", "docs")
        paths = {r.get("path") for r in rows}
        self.assertIn(".wavefoundry/framework/seeds/100-install.prompt.md", paths,
                      "framework seed must be folded into the project docs index")
        self.assertIn(".wavefoundry/framework/README.md", paths,
                      "framework README must be folded into the project docs index")
        self.assertIn("docs/guide.md", paths, "project docs must still be indexed")

        # The folded seed/README must also be tracked in meta.json file_meta (staleness).
        meta = _read_meta_store(self.root / ".wavefoundry" / "index")
        file_meta = meta.get("file_meta") or meta.get("file_hashes") or {}
        self.assertIn(".wavefoundry/framework/seeds/100-install.prompt.md", file_meta)
        self.assertIn(".wavefoundry/framework/README.md", file_meta)

    def test_docs_model_change_reembeds_docs_only_code_untouched(self):
        """1p4wx (AC-4): switching the DOCS model forces a docs-only re-embed via the
        existing ``model_versions['docs'] != DOCS_MODEL`` trigger. The realistic trigger
        path is content='docs' (the post-edit hook default), which never loads the code
        embedder — code vectors are left untouched."""
        _make_repo(self.root, {
            "src/foo.py": "def f():\n    return 1\n",
            "docs/guide.md": "## Intro\n\nWave lifecycle docs.\n",
        })
        self._run_build(full=True)
        index_dir = self.root / ".wavefoundry" / "index"
        meta = _read_meta_store(index_dir)
        # Simulate the docs-model upgrade: the index was built under an old docs model;
        # the code model still matches the current CODE_MODEL.
        code_class = self.bi._predicted_precision_class(
            self.bi.CODE_MODEL, self.bi._onnx_providers()
        )
        # Wave 1v454: the recorded fingerprint is class-scoped, so seed it through the same
        # helper the writer uses. Hardcoding the bare constant would look stale on a CPU-bound
        # machine (class int8) and trigger a re-embed this test is not about.
        code_fingerprint = self.bi._identity_fingerprint_for_class(code_class)
        meta.setdefault("model_versions", {})["docs"] = (
            f"old-docs-model@{code_class}@{code_fingerprint}"
        )
        meta["model_versions"]["code"] = (
            f"{self.bi.CODE_MODEL}@{code_class}@{code_fingerprint}"
        )
        _seed_meta_store(index_dir, meta)

        # Snapshot the code table before the docs re-embed.
        code_lance = index_dir / "code.lance"
        code_before = sorted(
            (p.name, p.stat().st_size) for p in code_lance.rglob("*") if p.is_file()
        ) if code_lance.is_dir() else []

        docs_calls: list[list[str]] = []
        docs_spy = _make_embedder_mock(dim=4, calls=docs_calls)
        # Only ONE embedder is provided: if the content='docs' build tried to load a
        # CODE embedder, side_effect would be exhausted and raise — proving code is untouched.
        with patch.object(self.bi, "_get_embedder", side_effect=[docs_spy]):
            self.bi.build_index(self.root, full=False, content="docs", verbose=False)

        embedded = [t for batch in docs_calls for t in batch]
        self.assertTrue(any("Wave lifecycle" in t for t in embedded),
                        "docs-model change must re-embed the docs layer")
        # meta now records the current docs model; code model untouched.
        meta_after = _read_meta_store(index_dir)
        # Wave 1p936: model_versions now carries a precision-class suffix ("@full" or "@int8"). The
        # class is machine-dependent (a CPU-bound box with the INT8 export cached records "@int8";
        # a GPU box or a box without the INT8 source records "@full"), so assert the MODEL-NAME
        # prefix, not the exact class.
        self.assertEqual(meta_after["model_versions"]["docs"].split("@", 1)[0], self.bi.DOCS_MODEL)
        self.assertEqual(meta_after["model_versions"]["code"], meta["model_versions"]["code"])
        # The code table files are byte-identical (never rewritten by the docs build).
        code_after = sorted(
            (p.name, p.stat().st_size) for p in code_lance.rglob("*") if p.is_file()
        ) if code_lance.is_dir() else []
        self.assertEqual(code_before, code_after, "code index must be untouched by a docs-only re-embed")

    def test_scoped_model_set_transition_converges_both_layers_atomically(self):
        """1v0r0 AC-6: a docs-scoped v1→v2 trigger cannot publish a mixed epoch."""
        _make_repo(self.root, {
            "src/foo.py": "def f():\n    return 1\n",
            "docs/guide.md": "## Intro\n\nWave lifecycle docs.\n",
        })
        self._run_build(full=True)
        index_dir = self.root / ".wavefoundry" / "index"
        meta = _read_meta_store(index_dir)
        # Change only the fingerprint under test, retaining the real producer's
        # machine-dependent precision instead of also requesting a conversion.
        meta["model_versions"] = {
            layer: "@".join(value.split("@")[:2]) + "@wf-model-set-1-legacy"
            for layer, value in meta["model_versions"].items()
        }
        _seed_meta_store(index_dir, meta)

        shared = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", return_value=shared):
            result = self.bi.build_index(
                self.root, full=False, content="docs", verbose=False
            )

        self.assertFalse(result.get("failed"), result)
        self.assertFalse(result.get("up_to_date", False))
        published = _read_meta_store(index_dir)["model_versions"]
        # Wave 1v454: expected fingerprint is class-scoped (int8 layers carry the encoding
        # revision), so derive it rather than pinning the bare constant.
        _expected_fp = self.bi._identity_fingerprint_for_class(
            self.bi._predicted_precision_class(self.bi.DOCS_MODEL, self.bi._onnx_providers())
        )
        self.assertEqual(
            self.bi._model_set_fingerprint_from_version(published["docs"]),
            _expected_fp,
        )
        self.assertEqual(
            self.bi._model_set_fingerprint_from_version(published["code"]),
            _expected_fp,
        )
        self.assertEqual(
            self.bi._model_set_fingerprint_from_version(published["docs"]),
            self.bi._model_set_fingerprint_from_version(published["code"]),
        )

    def test_explicit_rechunk_rechunks_all_reuses_vectors_no_version_change(self):
        """1p4n4 mode='rechunk': an explicit rechunk re-chunks EVERY file even with NO version
        change (a plain update would re-chunk nothing) while reusing embeddings by content hash —
        only new/changed chunks re-embed. Lets an operator re-materialize chunks after a chunker
        LOGIC change that was not version-bumped, cheaply."""
        _make_repo(self.root, {"src/foo.py": "def f():\n    return 1\n\ndef g():\n    return 2\n"})
        self._run_build(full=True)

        # A plain update with nothing changed re-chunks nothing.
        upd_calls: list[list[str]] = []
        with patch.object(self.bi, "_get_embedder", return_value=_make_embedder_mock(dim=4, calls=upd_calls)):
            r_upd = self.bi.build_index(self.root, full=False, content="code", verbose=False)
        self.assertEqual(r_upd.get("files_indexed"), 0, "plain update with no changes must re-chunk nothing")

        # rechunk re-processes every file but reuses vectors (nothing re-embedded), no version change.
        rc_calls: list[list[str]] = []
        with patch.object(self.bi, "_get_embedder", return_value=_make_embedder_mock(dim=4, calls=rc_calls)):
            r_rc = self.bi.build_index(self.root, full=False, rechunk=True, content="code", verbose=False)
        self.assertGreater(r_rc.get("files_indexed") or 0, 0, "rechunk must re-process every file")
        self.assertEqual([t for batch in rc_calls for t in batch], [],
                         "rechunk must reuse embeddings (content unchanged), not re-embed")

    def test_incremental_only_reindexes_changed_file(self):
        _make_repo(self.root, {
            "src/foo.py": "def f(): pass\n",
            "src/bar.py": "def g(): pass\n",
        })
        self._run_build(full=True)

        # Modify one file
        (self.root / "src" / "foo.py").write_text("def f(): return 1\n", encoding="utf-8")

        docs_mock = _make_embedder_mock(dim=4)
        code_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", side_effect=[docs_mock, code_mock]):
            result = self.bi.build_index(self.root, full=False, content="all", verbose=False)

        self.assertEqual(result["files_indexed"], 1)

    def test_incremental_markdown_embeds_only_changed_heading_chunk(self):
        _make_repo(self.root, {
            "docs/guide.md": textwrap.dedent("""\
                # Guide

                ## Alpha

                Alpha body stays the same.

                ## Beta

                Beta body before.
                """),
        })
        self._run_build(full=True)

        (self.root / "docs" / "guide.md").write_text(textwrap.dedent("""\
            # Guide

            ## Alpha

            Alpha body stays the same.

            ## Beta

            Beta body after.
            """), encoding="utf-8")

        doc_calls: list[list[str]] = []
        code_calls: list[list[str]] = []
        docs_mock = _make_embedder_mock(dim=4, calls=doc_calls)
        code_mock = _make_embedder_mock(dim=4, calls=code_calls)
        stdout = io.StringIO()
        with patch.object(self.bi, "_get_embedder", side_effect=[docs_mock, code_mock]):
            with contextlib.redirect_stdout(stdout):
                self.bi.build_index(self.root, full=False, content="all", verbose=False)

        embedded_doc_texts = [text for batch in doc_calls for text in batch]
        embedded_code_texts = [text for batch in code_calls for text in batch]
        self.assertEqual(len(embedded_doc_texts), 1)
        self.assertIn("Beta body after.", embedded_doc_texts[0])
        self.assertEqual(embedded_code_texts, [])
        self.assertRegex(
            stdout.getvalue(),
            r"semantic file update path=docs/guide\.md table=docs written=1 removed=1 unchanged=3",
        )

    def test_incremental_python_embeds_only_changed_code_chunk_for_mixed_path(self):
        _make_repo(self.root, {
            "src/tools.py": textwrap.dedent('''\
                def alpha():
                    """Alpha docs."""
                    return 1

                def beta():
                    return 2
                '''),
        })
        self._run_build(full=True)

        (self.root / "src" / "tools.py").write_text(textwrap.dedent('''\
            def alpha():
                """Alpha docs."""
                return 42

            def beta():
                return 2
            '''), encoding="utf-8")

        shared_calls: list[list[str]] = []
        shared_mock = _make_embedder_mock(dim=4, calls=shared_calls)
        stdout = io.StringIO()
        with patch.object(self.bi, "_get_embedder", return_value=shared_mock) as get:
            with contextlib.redirect_stdout(stdout):
                self.bi.build_index(self.root, full=False, content="all", verbose=False)

        embedded_texts = [text for batch in shared_calls for text in batch]
        get.assert_called_once()
        self.assertEqual(len(embedded_texts), 1)
        self.assertIn("return 42", embedded_texts[0])
        self.assertNotIn("def beta", embedded_texts[0])
        output = stdout.getvalue()
        self.assertRegex(output, r"semantic file update path=src/tools\.py table=docs written=0 removed=0 unchanged=1")
        self.assertRegex(output, r"semantic file update path=src/tools\.py table=code written=1 removed=1 unchanged=2")

    def test_incremental_line_window_shift_reembeds_affected_chunks(self):
        # 1sek8: the file must be CODE-CORPUS-ELIGIBLE under the unified
        # membership rule (source extensions + known extensionless code
        # names) — the former `.custom` fixture rode content=all's
        # unfiltered corpus, which no longer exists. Jenkinsfile is
        # line-window chunked by name, preserving the shift semantics
        # this test pins.
        source = "\n".join(f"line {i}" for i in range(1, 151)) + "\n"
        _make_repo(self.root, {"Jenkinsfile": source})
        self._run_build(full=True)

        shifted = "inserted line\n" + source
        (self.root / "Jenkinsfile").write_text(shifted, encoding="utf-8")

        shared_calls: list[list[str]] = []
        shared_mock = _make_embedder_mock(dim=4, calls=shared_calls)
        with patch.object(self.bi, "_get_embedder", return_value=shared_mock) as get:
            self.bi.build_index(self.root, full=False, content="all", verbose=False)

        embedded_code_texts = [text for batch in shared_calls for text in batch]
        get.assert_called_once()
        # Line-window ids are line-range based. A leading insertion changes the
        # window boundaries, so the safe behavior is to re-embed affected windows
        # instead of guessing at vector reuse.
        self.assertEqual(len(embedded_code_texts), 2)
        self.assertTrue(any("inserted line" in text for text in embedded_code_texts))

        rows = _read_index_chunks(self.root / ".wavefoundry" / "index", "code")
        shifted_rows = [row for row in rows if row["path"] == "Jenkinsfile"]
        self.assertTrue(any(row["lines"][0] > 1 for row in shifted_rows))
        self.assertTrue(all(row.get("chunk_hash") for row in shifted_rows))

    def test_meta_records_file_meta(self):
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        self._run_build(full=True)
        meta = _read_meta_store(self.root / ".wavefoundry" / "index")
        self.assertIn("file_meta", meta)
        self.assertIn("src/foo.py", meta["file_meta"])
        self.assertNotIn("file_hashes", meta)

    def test_meta_records_file_meta_with_stat_fields(self):
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        self._run_build(full=True)
        meta = _read_meta_store(self.root / ".wavefoundry" / "index")
        self.assertIn("file_meta", meta)
        entry = meta["file_meta"].get("src/foo.py")
        self.assertIsNotNone(entry)
        self.assertIn("hash", entry)
        self.assertIn("mtime", entry)
        self.assertIn("size", entry)
        self.assertIn("inode", entry)

    def test_meta_records_model_versions(self):
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        self._run_build(full=True)
        meta = _read_meta_store(self.root / ".wavefoundry" / "index")
        self.assertIn("docs", meta["model_versions"])
        self.assertIn("code", meta["model_versions"])

    def test_full_flag_ignores_existing_meta(self):
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        self._run_build(full=True)
        # Force full again — should reindex even though nothing changed
        result = self._run_build(full=True)
        self.assertFalse(result["up_to_date"])
        self.assertGreater(result["files_indexed"], 0)

    def test_removed_file_chunks_excluded_from_index(self):
        _make_repo(self.root, {
            "src/foo.py": "def f(): pass\n",
            "src/bar.py": "def g(): pass\n",
        })
        self._run_build(full=True)

        (self.root / "src" / "bar.py").unlink()

        docs_mock = _make_embedder_mock(dim=4)
        code_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", side_effect=[docs_mock, code_mock]):
            self.bi.build_index(self.root, full=False, content="all", verbose=False)

        code_chunks = _read_index_chunks(self.root / ".wavefoundry" / "index", "code")
        paths = {c["path"] for c in code_chunks}
        self.assertNotIn("src/bar.py", paths)

    def test_chunks_json_paths_use_forward_slashes(self):
        _make_repo(self.root, {"src/sub/foo.py": "def f(): pass\n"})
        self._run_build(full=True)
        code_chunks = _read_index_chunks(self.root / ".wavefoundry" / "index", "code")
        for c in code_chunks:
            self.assertNotIn("\\", c["path"])
            self.assertNotIn("\\", c["id"])

    def test_lance_row_count_matches_chunk_rows(self):
        _make_repo(self.root, {
            "src/foo.py": "def f(): pass\ndef g(): pass\n",
            "docs/guide.md": "## Intro\n\nHello.\n",
        })
        self._run_build(full=True)
        index_dir = self.root / ".wavefoundry" / "index"
        code_chunks = _read_index_chunks(index_dir, "code")
        docs_chunks = _read_index_chunks(index_dir, "docs")
        self.assertTrue((index_paths.runtime_database_path(index_dir)).is_file())
        self.assertTrue((index_paths.runtime_database_path(index_dir)).is_file())
        self.assertGreater(len(code_chunks), 0)
        self.assertGreater(len(docs_chunks), 0)

    def test_custom_index_dir_is_excluded_from_rebuild_hashes(self):
        _make_repo(self.root, {
            "docs/guide.md": "## Intro\n\nHello.\n",
            "framework/seeds/example.md": "## Seed\n\nExample.\n",
        })
        index_dir = self.root / "framework" / "index"
        index_dir.mkdir(parents=True, exist_ok=True)
        (index_dir / "stale.json").write_text('{"old": true}', encoding="utf-8")

        docs_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", return_value=docs_mock):
            self.bi.build_index(
                self.root,
                full=True,
                content="docs",
                index_dir=index_dir,
                include_prefixes=("framework",),
                verbose=False,
            )

        meta = _read_meta_store(index_dir)
        self.assertIn("framework/seeds/example.md", meta["file_meta"])
        self.assertNotIn("framework/index/stale.json", meta["file_meta"])

    def test_default_project_index_folds_framework_docs_but_excludes_other_framework_source(self):
        # Wave 1p4ww: the project docs index FOLDS the framework seeds + README, but the
        # rest of .wavefoundry/framework/ (scripts, MANIFEST, …) stays excluded by the
        # blanket .wavefoundry/ exclusion unless explicitly opted in via workflow-config.
        _make_repo(self.root, {
            "docs/guide.md": "## Intro\n\nHello.\n",
            ".wavefoundry/framework/README.md": "## Framework\n\nCanonical framework docs.\n",
            ".wavefoundry/framework/seeds/100-x.prompt.md": "# Seed\n\nBody.\n",
            ".wavefoundry/framework/scripts/server_impl.py": "def foo(): pass\n",
            ".wavefoundry/framework/MANIFEST": "README.md\nMANIFEST\n",
        })

        docs_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", return_value=docs_mock):
            self.bi.build_index(self.root, full=True, content="docs", verbose=False)

        index_dir = self.root / ".wavefoundry" / "index"
        meta = _read_meta_store(index_dir)
        chunks = _read_index_chunks(index_dir, "docs")
        chunk_paths = {c["path"] for c in chunks}
        self.assertIn("docs/guide.md", meta["file_meta"])
        # Folded framework docs ARE indexed.
        self.assertIn(".wavefoundry/framework/README.md", meta["file_meta"])
        self.assertIn(".wavefoundry/framework/seeds/100-x.prompt.md", meta["file_meta"])
        self.assertIn(".wavefoundry/framework/README.md", chunk_paths)
        self.assertIn(".wavefoundry/framework/seeds/100-x.prompt.md", chunk_paths)
        # Non-fold framework source stays excluded (not in the fold prefixes).
        self.assertNotIn(".wavefoundry/framework/scripts/server_impl.py", meta["file_meta"])
        self.assertNotIn(".wavefoundry/framework/MANIFEST", meta["file_meta"])
        self.assertFalse(any(c["path"] == ".wavefoundry/framework/scripts/server_impl.py" for c in chunks))

    def test_project_index_excludes_wavefoundry_blanket_except_folded_docs(self):
        """Wave 1p2q3 (1p2qd): all of .wavefoundry/ excluded from the project index —
        EXCEPT the framework docs folded in by 1p4ww (seeds + README)."""
        _make_repo(self.root, {
            "docs/guide.md": "## Intro\n\nHello.\n",
            ".wavefoundry/framework/scripts/server_impl.py": "def foo(): pass\n",
            ".wavefoundry/framework/dashboard/dashboard.js": "// dashboard\n",
            ".wavefoundry/framework/seeds/100.md": "## seed\n",
            ".wavefoundry/logs/event.log": "log\n",
            ".wavefoundry/state.json": "{}\n",
        })
        docs_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", return_value=docs_mock):
            self.bi.build_index(self.root, full=True, content="docs", verbose=False)
        index_dir = self.root / ".wavefoundry" / "index"
        meta = _read_meta_store(index_dir)
        fold_allowed = {".wavefoundry/framework/seeds/100.md"}
        for path in meta["file_meta"]:
            if path in fold_allowed:
                continue
            self.assertFalse(path.startswith(".wavefoundry/"),
                             f"unexpected .wavefoundry/ file in project meta: {path}")
        # The folded seed IS present.
        self.assertIn(".wavefoundry/framework/seeds/100.md", meta["file_meta"])

    def test_explicit_framework_index_can_include_framework_source(self):
        _make_repo(self.root, {
            "docs/guide.md": "## Intro\n\nHello.\n",
            ".wavefoundry/framework/README.md": "## Framework\n\nCanonical framework docs.\n",
            ".wavefoundry/framework/MANIFEST": "README.md\nMANIFEST\n",
        })

        index_dir = self.root / ".wavefoundry" / "framework" / "index"
        docs_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", return_value=docs_mock):
            self.bi.build_index(
                self.root,
                full=True,
                content="docs",
                index_dir=index_dir,
                include_prefixes=(".wavefoundry/framework",),
                respect_ignore=False,
                verbose=False,
            )

        meta = _read_meta_store(index_dir)
        chunks = _read_index_chunks(index_dir, "docs")
        self.assertIn(".wavefoundry/framework/README.md", meta["file_meta"])
        self.assertNotIn(".wavefoundry/framework/MANIFEST", meta["file_meta"])
        self.assertTrue(any(c["path"] == ".wavefoundry/framework/README.md" for c in chunks))
        self.assertFalse(any(c["path"] == ".wavefoundry/framework/MANIFEST" for c in chunks))

    def test_project_docs_index_can_opt_in_excluded_prefixes(self):
        _make_repo(self.root, {
            "docs/guide.md": "## Intro\n\nHello.\n",
            ".wavefoundry/framework/README.md": "## Framework\n\nCanonical framework docs.\n",
        })

        docs_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", return_value=docs_mock):
            self.bi.build_index(
                self.root,
                full=True,
                content="docs",
                project_include_prefixes=(".wavefoundry/framework",),
                verbose=False,
            )

        index_dir = self.root / ".wavefoundry" / "index"
        meta = _read_meta_store(index_dir)
        chunks = _read_index_chunks(index_dir, "docs")
        self.assertIn(".wavefoundry/framework/README.md", meta["file_meta"])
        self.assertTrue(any(c["path"] == ".wavefoundry/framework/README.md" for c in chunks))

    def test_project_code_index_can_opt_in_excluded_prefixes(self):
        _make_repo(self.root, {
            "src/app.py": "def app(): pass\n",
            ".wavefoundry/framework/scripts/server.py": "def server_main(): pass\n",
            "vendor/docs/custom.py": "def custom(): pass\n",
        })

        docs_mock = _make_embedder_mock(dim=4)
        code_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", side_effect=[docs_mock, code_mock]):
            self.bi.build_index(
                self.root,
                full=True,
                content="code",
                project_include_prefixes=(".wavefoundry/framework/scripts", "vendor/docs"),
                verbose=False,
            )

        index_dir = self.root / ".wavefoundry" / "index"
        meta = _read_meta_store(index_dir)
        code_chunks = _read_index_chunks(index_dir, "code")
        self.assertIn(".wavefoundry/framework/scripts/server.py", meta["file_meta"])
        self.assertTrue(any(c["path"] == ".wavefoundry/framework/scripts/server.py" for c in code_chunks))
        self.assertIn("vendor/docs/custom.py", meta["file_meta"])

    def test_project_meta_folds_framework_docs_only_and_is_stable_across_docs_and_code_runs(self):
        """Regression for 130nf + 1p4ww: project meta contains the FOLDED framework docs
        (seeds + README) but no other framework source, under any run; and consecutive docs
        and code runs must write identical file_meta dicts (the 'no alternating cycle'
        invariant — the fold lives in the shared files_for_meta surface, so it is stable).
        """
        _make_repo(self.root, {
            "docs/guide.md": "## Intro\n\nHello.\n",
            "src/app.py": "def app(): pass\n",
            ".wavefoundry/framework/README.md": "## Framework\n\nCanonical framework docs.\n",
            ".wavefoundry/framework/seeds/100-x.prompt.md": "# Seed\n\nBody.\n",
            ".wavefoundry/framework/MANIFEST": "README.md\nMANIFEST\n",
            ".wavefoundry/framework/scripts/tools.py": "def helper():\n    return 1\n",
        })
        (self.root / "docs" / "workflow-config.json").write_text(
            json.dumps({"indexing": {"project_include_prefixes": {"docs": [], "code": []}}}),
            encoding="utf-8",
        )

        index_dir = self.root / ".wavefoundry" / "index"
        folded = {".wavefoundry/framework/README.md", ".wavefoundry/framework/seeds/100-x.prompt.md"}

        # Run 1: docs only.
        with patch.object(self.bi, "_get_embedder", return_value=_make_embedder_mock(dim=4)):
            self.bi.build_index(self.root, full=True, content="docs", verbose=False)
        meta_after_docs = _read_meta_store(index_dir)["file_meta"]

        # Only the FOLDED framework docs appear — not MANIFEST or scripts.
        framework_in_meta = {p for p in meta_after_docs if p.startswith(".wavefoundry/framework/")}
        self.assertEqual(framework_in_meta, folded, f"unexpected framework files in project meta: {framework_in_meta}")
        self.assertIn("docs/guide.md", meta_after_docs)
        self.assertIn("src/app.py", meta_after_docs)

        # Run 2: code only — incremental, on top of the docs meta
        with patch.object(self.bi, "_get_embedder", side_effect=[_make_embedder_mock(dim=4), _make_embedder_mock(dim=4)]):
            self.bi.build_index(self.root, full=False, content="code", verbose=False)
        meta_after_code = _read_meta_store(index_dir)["file_meta"]

        # Still only the folded framework docs in project meta after the code run.
        framework_in_meta = {p for p in meta_after_code if p.startswith(".wavefoundry/framework/")}
        self.assertEqual(framework_in_meta, folded, f"unexpected framework files after code run: {framework_in_meta}")

        # Stability invariant: docs run and code run must write IDENTICAL meta keys
        # (the original line-1822 fix prevented the 93-added/93-removed alternating cycle;
        # the new narrowing must preserve it).
        self.assertEqual(
            set(meta_after_docs.keys()),
            set(meta_after_code.keys()),
            "docs-run and code-run wrote different project meta — alternating cycle would resume",
        )

    def test_fold_survives_forwarded_non_empty_override_prefixes(self):
        """Regression (1p4ww × self-hosting): a launcher that FORWARDS non-empty
        project include-prefixes — e.g. setup_index merging the workflow-config
        code prefix ``.wavefoundry/framework/scripts`` and passing it as
        ``project_include_prefixes`` — must NOT disable the framework-seed fold.

        The override path previously returned early WITHOUT appending
        ``FRAMEWORK_FOLD_DOCS_PREFIXES``, so the moment a project configured ANY
        code prefix the override became non-empty and every seed silently vanished
        from the docs index (observed: 0/67 seeds after a real rebuild)."""
        _make_repo(self.root, {
            "docs/guide.md": "## Intro\n\nHello.\n",
            ".wavefoundry/framework/README.md": "## Framework\n\nCanonical.\n",
            ".wavefoundry/framework/seeds/100-x.prompt.md": "# Seed\n\nBody.\n",
            ".wavefoundry/framework/scripts/tools.py": "def helper():\n    return 1\n",
        })
        index_dir = self.root / ".wavefoundry" / "index"
        folded = {".wavefoundry/framework/README.md", ".wavefoundry/framework/seeds/100-x.prompt.md"}

        # content="all" with a FORWARDED override prefix (the setup_index merge result).
        with patch.object(self.bi, "_get_embedder",
                          side_effect=[_make_embedder_mock(dim=4), _make_embedder_mock(dim=4)]):
            self.bi.build_index(
                self.root,
                full=True,
                content="all",
                project_include_prefixes=(".wavefoundry/framework/scripts",),
                verbose=False,
            )

        meta = _read_meta_store(index_dir)["file_meta"]
        docs_chunks = {c["path"] for c in _read_index_chunks(index_dir, "docs")}

        # The forwarded code prefix is honored...
        self.assertIn(".wavefoundry/framework/scripts/tools.py", meta)
        # ...AND the folded seeds survive into both meta and the docs index.
        for path in folded:
            self.assertIn(path, meta, f"folded seed dropped from meta when override present: {path}")
            self.assertIn(path, docs_chunks, f"folded seed not embedded into docs index: {path}")

    def test_docs_only_graph_includes_workflow_code_prefixes_without_cli_args(self):
        _make_repo(self.root, {
            "docs/guide.md": "## Intro\n\nHello.\n",
            ".wavefoundry/framework/scripts/tools.py": "def helper():\n    return 1\n",
        })
        (self.root / "docs" / "workflow-config.json").write_text(
            json.dumps(
                {
                    "lifecycle_id_policy": {"epoch_utc": "2020-02-02T02:02:00Z", "hour_offset": 0},
                    "indexing": {
                        "project_include_prefixes": {
                            "docs": [],
                            "code": [".wavefoundry/framework/scripts"],
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        docs_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", return_value=docs_mock):
            self.bi.build_index(
                self.root,
                full=True,
                content="docs",
                verbose=False,
            )
        graph = _published_graph_payload(self.bi, self.root)
        node_ids = {n["id"] for n in graph.get("nodes", [])}
        self.assertIn(".wavefoundry/framework/scripts/tools.py::helper", node_ids)

    def test_code_pass_self_reads_workflow_code_prefixes_without_cli_args(self):
        _make_repo(self.root, {
            "src/app.py": "def app(): pass\n",
            ".wavefoundry/framework/scripts/server.py": "def server_main(): pass\n",
        })
        (self.root / "docs" / "workflow-config.json").write_text(
            json.dumps(
                {
                    "indexing": {
                        "project_include_prefixes": {
                            "docs": [],
                            "code": [".wavefoundry/framework/scripts"],
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        docs_mock = _make_embedder_mock(dim=4)
        code_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", side_effect=[docs_mock, code_mock]):
            self.bi.build_index(
                self.root,
                full=True,
                content="code",
                verbose=False,
            )
        index_dir = self.root / ".wavefoundry" / "index"
        meta = _read_meta_store(index_dir)
        code_chunks = _read_index_chunks(index_dir, "code")
        self.assertIn(".wavefoundry/framework/scripts/server.py", meta["file_meta"])
        self.assertTrue(
            any(c["path"] == ".wavefoundry/framework/scripts/server.py" for c in code_chunks)
        )

    def test_legacy_include_framework_boolean_indexes_framework_scripts(self):
        _make_repo(self.root, {
            "src/app.py": "def app(): pass\n",
            ".wavefoundry/framework/scripts/server.py": "def server_main(): pass\n",
        })
        (self.root / "docs" / "workflow-config.json").write_text(
            json.dumps(
                {"indexing": {"include_framework_code_for_code_search": True}}
            ),
            encoding="utf-8",
        )
        docs_mock = _make_embedder_mock(dim=4)
        code_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", side_effect=[docs_mock, code_mock]):
            self.bi.build_index(
                self.root,
                full=True,
                content="code",
                verbose=False,
            )
        index_dir = self.root / ".wavefoundry" / "index"
        meta = _read_meta_store(index_dir)
        self.assertIn(".wavefoundry/framework/scripts/server.py", meta["file_meta"])

    def test_workflow_config_evolution_reaps_orphaned_lance_rows(self):
        """Wave 1p31b (1p312): incremental update must reap LanceDB rows for
        paths excluded by workflow-config evolution, even when meta.json and
        the on-disk eligible set both already reflect the post-narrowing
        state (the post-evolution stable state where the reaper is the only
        thing that can detect the LanceDB orphan condition).

        Simulates the bug pattern in its hardest form: a prior build correctly
        cleaned meta.json AND the now-ineligible files no longer exist in the
        eligible set on disk, but earlier eviction failed to remove the
        LanceDB rows. Subsequent incrementals see "current matches meta" and
        treat the index as up-to-date — the orphan condition is invisible to
        the existing change-detection logic, so the reaper is the only
        guarantee that orphans are removed.
        """
        # Build with both src/ and lib/ indexed.
        _make_repo(self.root, {
            "src/app.py": "def app(): pass\n",
            "lib/helper.py": "def help(): pass\n",
            "lib/another.py": "def other(): pass\n",
        })
        self._run_build(full=True)

        index_dir = self.root / ".wavefoundry" / "index"

        # Confirm starting state: lib/ paths are in LanceDB.
        code_chunks_before = _read_index_chunks(index_dir, "code")
        paths_before = {c["path"] for c in code_chunks_before}
        self.assertIn("lib/helper.py", paths_before)
        self.assertIn("lib/another.py", paths_before)

        # Simulate post-evolution stable state:
        # 1. Trim meta.json to drop lib/ (workflow-config narrowing was applied).
        # 2. Delete the lib/ files from disk (the eligibility set narrowed and a
        #    subsequent run dropped them from meta, but earlier eviction failed
        #    to remove the LanceDB rows). This is the silent-orphan condition
        #    every operator with an evolving workflow-config accumulates.
        meta = _read_meta_store(index_dir)
        meta["file_meta"] = {
            k: v for k, v in meta["file_meta"].items()
            if not k.startswith("lib/")
        }
        _seed_meta_store(index_dir, meta)
        (self.root / "lib" / "helper.py").unlink()
        (self.root / "lib" / "another.py").unlink()

        # Run incremental update. From _detect_changes' perspective the index
        # is up-to-date (current eligible matches meta, both exclude lib/),
        # but LanceDB still has lib/ rows. The reaper must catch and remove
        # them on the up-to-date path itself.
        result = self.bi.build_index(self.root, full=False, content="all", verbose=False)

        # Reaper count surfaces in response.
        self.assertIn("stranded_rows_reaped", result)
        self.assertGreater(result["stranded_rows_reaped"], 0, msg="reaper should report > 0 orphans removed")

        # LanceDB no longer contains lib/ paths.
        code_chunks_after = _read_index_chunks(index_dir, "code")
        paths_after = {c["path"] for c in code_chunks_after}
        self.assertNotIn("lib/helper.py", paths_after)
        self.assertNotIn("lib/another.py", paths_after)
        # src/app.py survives — it was never excluded.
        self.assertIn("src/app.py", paths_after)

    def test_reaper_idempotent_on_clean_index(self):
        """Wave 1p31b (1p312): subsequent reaper runs on an already-clean
        index report stranded_rows_reaped: 0. Verifies AC-5 second-half:
        once orphans are reaped, future runs surface 0."""
        _make_repo(self.root, {
            "src/foo.py": "def f(): pass\n",
            "src/bar.py": "def g(): pass\n",
        })
        self._run_build(full=True)
        # First incremental on a clean (no orphan) index.
        result = self.bi.build_index(self.root, full=False, content="all", verbose=False)
        self.assertEqual(result.get("stranded_rows_reaped", 0), 0)
        # Second incremental on a clean index.
        result2 = self.bi.build_index(self.root, full=False, content="all", verbose=False)
        self.assertEqual(result2.get("stranded_rows_reaped", 0), 0)


class StatCacheTests(unittest.TestCase):
    """12b1a: stat+inode cache pre-filter for incremental change detection."""

    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _run_build(self, full: bool = False) -> dict:
        docs_mock = _make_embedder_mock(dim=4)
        code_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", side_effect=[docs_mock, code_mock]):
            return self.bi.build_index(self.root, full=full, content="all", verbose=False)

    def test_stat_cache_hit_skips_hash_on_clean_pass(self):
        """Clean source files retain stat-cache hits; configuration is fenced separately."""
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        self._run_build(full=True)
        with patch.object(self.bi, "_sha256", wraps=self.bi._sha256) as mock_hash:
            result = self.bi.build_index(self.root, full=False, content="all", verbose=False)
        self.assertTrue(result["up_to_date"])
        self.assertEqual(mock_hash.call_args_list,
                         [unittest.mock.call(self.root / "docs" / "workflow-config.json")])

    def test_stat_cache_miss_on_content_change(self):
        """A file whose content changes is detected and re-chunked."""
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        self._run_build(full=True)
        (self.root / "src" / "foo.py").write_text("def f(): return 42\n", encoding="utf-8")
        result = self._run_build(full=False)
        self.assertFalse(result["up_to_date"])
        self.assertEqual(result["files_indexed"], 1)

    def test_same_content_same_mtime_not_rechunked(self):
        """A file written with identical content and restored mtime is not re-chunked."""
        p = self.root / "src" / "foo.py"
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        self._run_build(full=True)
        # Capture original mtime
        original_mtime = p.stat().st_mtime
        # Overwrite with identical content, restore mtime
        p.write_text("def f(): pass\n", encoding="utf-8")
        import os
        os.utime(p, (original_mtime, original_mtime))
        result = self.bi.build_index(self.root, full=False, content="all", verbose=False)
        self.assertTrue(result["up_to_date"])

    def test_missing_file_meta_treated_as_empty(self):
        """An index with no file_meta is treated as empty — all files re-hashed."""
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        index_dir = self.root / ".wavefoundry" / "index"
        index_dir.mkdir(parents=True, exist_ok=True)
        _seed_meta_store(index_dir, {
                "model_versions": {"docs": self.bi.DOCS_MODEL, "code": self.bi.CODE_MODEL},
                "chunker_version": "",
            })
        result = self._run_build(full=False)
        meta = _read_meta_store(index_dir)
        self.assertIn("file_meta", meta)
        entry = meta["file_meta"].get("src/foo.py")
        self.assertIsNotNone(entry)
        self.assertIn("mtime", entry)

    def test_full_rebuild_bypasses_stat_cache(self):
        """Full rebuild re-hashes all files regardless of cached stat."""
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        self._run_build(full=True)
        with patch.object(self.bi, "_sha256", wraps=self.bi._sha256) as mock_hash:
            result = self._run_build(full=True)
        self.assertFalse(result["up_to_date"])
        mock_hash.assert_called()


class ModelVersionChangeTests(unittest.TestCase):
    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_model_version_change_triggers_full_rebuild(self):
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        index_dir = self.root / ".wavefoundry" / "index"
        index_dir.mkdir(parents=True, exist_ok=True)
        # Write stale meta with old model name
        _seed_meta_store(index_dir, {
                "model_versions": {"docs": "old-model", "code": "old-model"},
                "file_meta": {},
            })
        docs_mock = _make_embedder_mock(dim=4)
        code_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", side_effect=[docs_mock, code_mock]):
            result = self.bi.build_index(self.root, full=False, content="all", verbose=False)
        self.assertFalse(result["up_to_date"])
        self.assertGreater(result["files_indexed"], 0)

    def test_chunker_version_change_per_layer_triggers_rebuild(self):
        """A docs-only update must not stamp the code layer as current (regression guard)."""
        _make_repo(self.root, {"src/foo.md": "## Guide\n\nContent.\n"})
        index_dir = self.root / ".wavefoundry" / "index"
        index_dir.mkdir(parents=True, exist_ok=True)
        current_cv = self.bi._get_chunker().CHUNKER_VERSION
        # Simulate: code layer was built with an old chunker; docs layer is current
        _seed_meta_store(index_dir, {
                "model_versions": {
                    "docs": self.bi.DOCS_MODEL,
                    "code": self.bi.CODE_MODEL,
                },
                "chunker_versions": {
                    "docs": current_cv,
                    "code": "0",
                },
                "content": ["docs", "code"],
                "file_meta": {},
            })
        # A code-only update must detect the stale chunker and force a full rebuild
        docs_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", return_value=docs_mock):
            result = self.bi.build_index(self.root, full=False, content="code", verbose=False)
        self.assertFalse(result.get("up_to_date", False))
        # After the build, the code layer must record the current chunker version
        meta = _read_meta_store(index_dir)
        self.assertEqual(meta["chunker_versions"]["code"], current_cv)

    def test_legacy_chunker_version_scalar_migrated(self):
        """Old meta with scalar chunker_version is treated as applying to both layers."""
        _make_repo(self.root, {"src/foo.md": "## Guide\n\nContent.\n"})
        index_dir = self.root / ".wavefoundry" / "index"
        index_dir.mkdir(parents=True, exist_ok=True)
        current_cv = self.bi._get_chunker().CHUNKER_VERSION
        # Legacy format: single scalar, not per-layer
        _seed_meta_store(index_dir, {
                "model_versions": {
                    "docs": self.bi.DOCS_MODEL,
                    "code": self.bi.CODE_MODEL,
                },
                "chunker_version": "old-chunker",
                "content": ["docs", "code"],
                "file_meta": {},
            })
        docs_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", return_value=docs_mock):
            result = self.bi.build_index(self.root, full=False, content="docs", verbose=False)
        # Must trigger a rebuild since old-chunker != current
        self.assertFalse(result.get("up_to_date", False))
        # New meta must use chunker_versions dict, not scalar
        meta = _read_meta_store(index_dir)
        self.assertIn("chunker_versions", meta)
        self.assertEqual(meta["chunker_versions"]["docs"], current_cv)


    def test_graph_only_rebuild_preserves_docs_code_chunker_versions(self):
        """graph-only rebuild must not wipe docs/code chunker_versions from metadata."""
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        index_dir = self.root / ".wavefoundry" / "index"
        index_dir.mkdir(parents=True, exist_ok=True)
        current_cv = self.bi._get_chunker().CHUNKER_VERSION
        _seed_meta_store(index_dir, {
                "model_versions": {
                    "docs": self.bi.DOCS_MODEL,
                    "code": self.bi.CODE_MODEL,
                },
                "chunker_versions": {
                    "docs": current_cv,
                    "code": current_cv,
                },
                "walker_version": self.bi.WALKER_VERSION,
                "content": ["docs", "code"],
                "file_meta": {},
            })
        self.bi.build_index(self.root, full=True, content="graph", verbose=False)
        meta = _read_meta_store(index_dir)
        self.assertEqual(meta.get("chunker_versions", {}).get("docs"), current_cv)
        self.assertEqual(meta.get("chunker_versions", {}).get("code"), current_cv)
        self.assertIn("docs", meta.get("content", []))
        self.assertIn("code", meta.get("content", []))



class ExplicitPrecisionRebuildTests(unittest.TestCase):
    """Real public builds with deterministic vectors; no native model downloads."""

    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "docs").mkdir()
        (self.root / "src").mkdir()
        (self.root / "docs/guide.md").write_text("# Guide\n\nOriginal precision fixture.\n")
        (self.root / "docs/stable.md").write_text("# Stable\n\nUnchanged sentinel document.\n")
        (self.root / "src/example.py").write_text("def example():\n    return 7\n")
        self.index_dir = self.root / ".wavefoundry/index"
        self.calls = []
        self.embedder = _make_embedder_mock(calls=self.calls)

    def _build(self, precision, **kwargs):
        providers = ["CoreMLExecutionProvider"] if precision == "full" else ["CPUExecutionProvider"]
        with patch.object(self.bi, "_onnx_providers", return_value=providers), \
             patch.object(self.bi, "_predicted_precision_class", side_effect=lambda model, selected:
                          "full" if "CoreMLExecutionProvider" in selected else "int8"), \
             patch.object(self.bi, "_get_embedder", return_value=self.embedder) as factory, \
             redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.last_factory = factory
            return self.bi.build_index(self.root, **kwargs)

    def _seed(self, precision="full"):
        result = self._build(precision, full=True, content="all")
        self.assertFalse(result.get("failed"), result)
        self.assertTrue(self.calls, "fixture must actually embed")
        self.calls.clear()

    def _snapshot(self):
        # Use the production APSW binding, including all canonical bookkeeping,
        # provenance, vectors, graph, path state, and build epoch rows.
        conn = self.bi._get_index_state_store().open_read_only(self.index_dir)
        self.assertIsNotNone(conn)
        try:
            schema = list(conn.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY name"))
            tables = [row[1] for row in schema if row[0] == "table"]
            return schema, {name: sorted(conn.execute('SELECT * FROM "' + name.replace('"', '""') + '"'), key=repr)
                            for name in tables}
        finally:
            conn.close()

    def _refuse(self, precision, **kwargs):
        before = self._snapshot()
        store = self.bi._get_index_state_store()
        with patch.object(self.bi, "_resolve_build_embedders", wraps=self.bi._resolve_build_embedders) as resolve, \
             patch.object(store, "begin_build_epoch", wraps=store.begin_build_epoch) as idle, \
             patch.object(store, "begin_recoverable_build_epoch", wraps=store.begin_recoverable_build_epoch) as epoch:
            result = self._build(precision, **kwargs)
        self.assertTrue(result.get("failed"), result)
        self.assertFalse(result["up_to_date"])
        self.assertIn("Implicit precision conversion refused", result["failure"])
        self.assertIn("wf setup --full", result["failure"])
        self.assertIn("provider environment", result["failure"])
        resolve.assert_not_called()
        self.last_factory.assert_not_called()
        idle.assert_not_called()
        epoch.assert_not_called()
        self.assertEqual(self.calls, [])
        self.assertEqual(self._snapshot(), before)
        return result

    def test_both_directions_all_scopes_and_dry_run_preserve_published_state(self):
        for recorded, requested in (("full", "int8"), ("int8", "full")):
            self._seed(recorded)
            for content in ("docs", "code", "all", "graph"):
                for dry_run in (False, True):
                    with self.subTest(recorded=recorded, content=content, dry_run=dry_run):
                        result = self._refuse(requested, content=content, dry_run=dry_run)
                        self.assertEqual(result["precision_changes"], [
                            {"layer": layer, "recorded": recorded, "requested": requested}
                            for layer in ("docs", "code")])

    def test_real_precision_predictor_observes_provider_fallback(self):
        self.assertIsNotNone(self.bi.accel_embedder)
        self.assertIn(self.bi.DOCS_MODEL, self.bi.accel_embedder.CLEAN_ONNX_SOURCES)
        with patch.object(self.bi, "_onnx_providers", return_value=["CoreMLExecutionProvider"]), \
             patch.object(self.bi.accel_embedder, "_available_gpu_providers", return_value=["CoreMLExecutionProvider"]), \
             patch.object(self.bi, "_get_embedder", return_value=self.embedder), \
             redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            built = self.bi.build_index(self.root, content="all")
        self.assertFalse(built.get("failed"), built)
        self.assertTrue(self.calls)
        self.calls.clear()
        before = self._snapshot()
        with patch.object(self.bi, "_onnx_providers", return_value=["CPUExecutionProvider"]), \
             patch.object(self.bi.accel_embedder, "_available_gpu_providers", return_value=[]), \
             patch.object(self.bi, "_get_embedder") as factory, redirect_stderr(io.StringIO()):
            refused = self.bi.build_index(self.root, content="all")
        self.assertTrue(refused.get("failed"), refused)
        self.assertEqual(refused["precision_changes"], [
            {"layer": layer, "recorded": "full", "requested": "int8"} for layer in ("docs", "code")])
        factory.assert_not_called()
        self.assertEqual(self._snapshot(), before)

    def test_targeted_and_rechunk_updates_cannot_escalate_precision(self):
        self._seed()
        for options in ({"files": [self.root / "docs/guide.md"]}, {"rechunk": True}):
            with self.subTest(options=options):
                self._refuse("int8", content="docs", **options)

    def test_untouched_sibling_precision_is_checked(self):
        with patch.object(self.bi, "DOCS_MODEL", "fixture-docs"), patch.object(self.bi, "CODE_MODEL", "fixture-code"):
            self._seed()
            before = self._snapshot()
            with patch.object(self.bi, "_predicted_precision_class", side_effect=lambda model, providers:
                              "int8" if model == "fixture-code" else "full"), \
                 patch.object(self.bi, "_get_embedder") as embed, redirect_stderr(io.StringIO()):
                result = self.bi.build_index(self.root, content="docs")
            self.assertTrue(result.get("failed"), result)
            self.assertEqual(result["precision_changes"], [{"layer": "code", "recorded": "full", "requested": "int8"}])
            embed.assert_not_called()
            self.assertEqual(self._snapshot(), before)

    def test_compatible_restore_is_incremental_and_explicit_full_reembeds(self):
        self._seed()
        self._refuse("int8", content="all")
        restored = self._build("full", content="all")
        self.assertFalse(restored.get("failed"), restored)
        self.assertEqual(self.calls, [], "compatible environment must reuse existing vectors")
        (self.root / "docs/guide.md").write_text("# Guide\n\nChanged incremental sentinel.\n")
        changed = self._build("full", content="all")
        self.assertFalse(changed.get("failed"), changed)
        embedded = "\n".join(text for batch in self.calls for text in batch)
        self.assertIn("Changed incremental sentinel", embedded)
        self.assertNotIn("Unchanged sentinel document", embedded)
        self.calls.clear()
        for precision in ("int8", "full"):
            result = self._build(precision, full=True, content="all")
            self.assertFalse(result.get("failed"), result)
            self.assertTrue(self.calls, "explicit conversion must really embed")
            meta = _read_meta_store(self.index_dir)
            self.assertTrue(all(value.split("@")[1] == precision for value in meta["model_versions"].values()))
            self.calls.clear()

    def test_fresh_cpu_install_and_same_class_model_revision_remain_allowed(self):
        fresh = self._build("int8", full=False, content="all")
        self.assertFalse(fresh.get("failed"), fresh)
        self.assertTrue(self.calls, "fresh CPU install must enter normal embedding")
        self.calls.clear()
        unchanged = self._build("int8", content="all")
        self.assertFalse(unchanged.get("failed"), unchanged)
        self.assertEqual(self.calls, [])
        with patch.object(self.bi, "EMBEDDING_MODEL_SET_FINGERPRINT", "fixture-genuine-revision"):
            result = self._build("int8", content="docs")
        self.assertFalse(result.get("failed"), result)
        self.assertTrue(self.calls, "genuine same-precision revision must reembed")
        self.assertIn("fixture-genuine-revision", _read_meta_store(self.index_dir)["model_versions"]["docs"])

    def test_unknown_and_missing_legacy_precision_keep_reconstruction_path(self):
        for spelling in ("bare", "unknown", "missing"):
            self._seed()
            meta = _read_meta_store(self.index_dir)
            for layer in ("docs", "code"):
                model = meta["model_versions"][layer].split("@")[0]
                if spelling == "missing":
                    meta["model_versions"].pop(layer)
                else:
                    meta["model_versions"][layer] = model if spelling == "bare" else model + "@unrecognized@old"
            _seed_meta_store(self.index_dir, meta)  # explicit damaged-provenance variant of a real built index
            with self.subTest(spelling=spelling):
                if spelling == "missing":
                    before = self._snapshot()
                    with self.assertRaises(self.bi.index_compatibility.IndexCompatibilityError) as caught:
                        self._build("int8", content="all")
                    self.assertEqual(caught.exception.code, "index_compatibility_unproven")
                    self.assertEqual(self._snapshot(), before)
                    self.assertEqual(self.calls, [])
                else:
                    result = self._build("int8", content="all")
                    self.assertFalse(result.get("failed"), result)
                    self.assertTrue(self.calls)
                    self.calls.clear()

    def test_guard_removal_is_detected_by_public_build_oracle(self):
        self._seed()
        with patch.object(self.bi, "_implicit_precision_changes", return_value=[]):
            with self.assertRaises(AssertionError):
                self._refuse("int8", content="all")
        self.assertTrue(self.calls, "the mutant must demonstrate the expensive reembedding regression")

    def test_setup_consumes_real_refusal_without_claiming_an_incomplete_epoch(self):
        from test_setup_index import load_setup_index
        setup = load_setup_index()
        self._seed()
        before = self._snapshot()
        calls = []
        def run_indexer(root, *, full=False, content="all", **kwargs):
            calls.append((content, full))
            # Execute the real indexer CLI producer; only the process boundary
            # is substituted, so failure text and exit status are not fixtures.
            args = ["--root", str(root), "--content", content] + (["--full"] if full else [])
            code = self.bi.main(args)
            if code:
                raise subprocess.CalledProcessError(code, args)
        for graph_only in (False, True):
            with self.subTest(graph_only=graph_only), \
                 patch.object(self.bi, "_predicted_precision_class", return_value="int8"), \
                 patch.object(self.bi, "_get_embedder") as embed, \
                 patch.object(setup, "ensure_deps"), \
                 patch.object(setup, "_reexec_with_venv_if_needed"), \
                 patch.object(setup, "_workflow_project_include_prefixes", return_value={}), \
                 patch.object(setup, "_indexer_models", return_value=[]), \
                 patch.object(setup, "prewarm_models"), \
                 patch.object(setup, "report_embedding_provider_decision"), \
                 patch.object(setup, "_prewarm_gpu_accel"), \
                 patch.object(setup, "_run_indexer", side_effect=run_indexer), \
                 redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()) as err:
                code = setup.main(["--root", str(self.root)] + (["--graph-only"] if graph_only else []))
            self.assertEqual(code, 2)
            self.assertIn("Implicit precision conversion refused", err.getvalue())
            self.assertIn("index build failed (exit 1)", err.getvalue())
            self.assertNotIn("epoch was left incomplete", err.getvalue())
            self.assertNotIn("readers fail closed", err.getvalue())
            self.assertNotIn("Done.", out.getvalue())
            embed.assert_not_called()
        self.assertEqual(calls, [("all", False), ("graph", False)])
        self.assertEqual(self._snapshot(), before)

    def test_mcp_consumes_real_cli_refusal_and_graph_update_does_not_force_full(self):
        # Loading the MCP composition root deliberately purges sibling modules.
        # Isolate that behavior so this producer test cannot invalidate another
        # test's already-imported module identity.
        script = (
            "import unittest; from test_indexer import ExplicitPrecisionRebuildTests; "
            "suite=unittest.TestSuite([ExplicitPrecisionRebuildTests('_check_mcp_consumer')]); "
            "result=unittest.TextTestRunner().run(suite); raise SystemExit(not result.wasSuccessful())"
        )
        result = subprocess.run([sys.executable, "-B", "-c", script],
            env=dict(os.environ, PYTHONPATH=os.pathsep.join((str(SCRIPTS_ROOT), str(SCRIPTS_ROOT / "tests")))),
            capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def _check_mcp_consumer(self):
        from server_tools_support import load_server
        server = load_server()
        self._seed()
        before = self._snapshot()
        commands = []
        def spawn(command, **kwargs):
            commands.append(command)
            content = "graph" if "--graph-only" in command else command[command.index("--content") + 1]
            args = ["--root", str(self.root), "--content", content] + (["--full"] if "--full" in command else [])
            with redirect_stdout(kwargs["stdout"]), redirect_stderr(kwargs["stdout"]):
                code = self.bi.main(args)
            kwargs["stdout"].flush()
            return MagicMock(pid=999999, poll=MagicMock(return_value=code))
        for content in ("docs", "graph"):
            with self.subTest(content=content), \
                 patch.object(self.bi, "_predicted_precision_class", return_value="int8"), \
                 patch.object(self.bi, "_get_embedder") as embed, \
                 patch("index_handlers._index_is_up_to_date", return_value=False), \
                 patch("index_handlers._index_build_active", return_value=False), \
                 patch.object(server, "_INDEX_BUILD_VERIFY_TIMEOUT_SECONDS", 0.5), \
                 patch("subprocess.Popen", side_effect=spawn):
                result = server.index_build_response(self.root, content=content, mode="update")
            self.assertEqual(result["status"], "error", result)
            self.assertTrue(result["data"]["build_failed_early"])
            self.assertFalse(result["data"]["passed"])
            self.assertFalse(result["data"]["graph_rebuilt"])
            self.assertIn("Implicit precision conversion refused", str(result))
            embed.assert_not_called()
        self.assertTrue(commands)
        self.assertTrue(all("--full" not in command for command in commands))
        self.assertEqual(self._snapshot(), before)

    def test_indexer_cli_returns_failure_from_real_preflight(self):
        self._seed()
        before = self._snapshot()
        with patch.object(self.bi, "_predicted_precision_class", return_value="int8"), \
             patch.object(self.bi, "_get_embedder") as embed, \
             redirect_stderr(io.StringIO()) as err, redirect_stdout(io.StringIO()):
            code = self.bi.main(["--root", str(self.root), "--content", "all"])
        self.assertEqual(code, 1)
        self.assertIn("Implicit precision conversion refused", err.getvalue())
        embed.assert_not_called()
        self.assertEqual(self._snapshot(), before)


class PrecisionClassVersionTests(unittest.TestCase):
    """Wave 1p936: the precision class (``full`` vs ``int8``) folded into ``model_versions`` —
    an explicit class conversion re-embeds; a same-class provider/format swap (FP16<->FP32) does not."""

    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    # --- the pure helpers (deterministic, no hardware / no build) ---

    def test_precision_class_from_version_parses_suffix(self):
        self.assertEqual(self.bi._precision_class_from_version("MODEL@int8"), "int8")
        self.assertEqual(self.bi._precision_class_from_version("MODEL@full"), "full")

    def test_precision_class_from_version_legacy_bare_name_is_full(self):
        # AC-3: a legacy value with no "@class" suffix predates the precision split → "full"
        # (existing indexes are full-precision; must not spuriously rebuild on upgrade).
        self.assertEqual(self.bi._precision_class_from_version("Snowflake/snowflake-arctic-embed-s"), "full")
        self.assertEqual(self.bi._precision_class_from_version(""), "full")
        self.assertEqual(self.bi._precision_class_from_version(None), "full")

    def test_predicted_precision_class_gpu_is_full(self):
        # A GPU machine runs FP16 end-to-end → "full" (a non-offloading model falls back to
        # fastembed full, never int8 — so "GPU available" always means "full").
        self.assertEqual(
            self.bi._predicted_precision_class("Snowflake/snowflake-arctic-embed-s", ["CoreMLExecutionProvider"]),
            "full",
        )

    def test_predicted_precision_class_cpu_registered_is_int8(self):
        # No GPU + a model with an INT8 clean-export source → "int8".
        with patch.object(self.bi.accel_embedder, "_available_gpu_providers", return_value=[]):
            self.assertEqual(
                self.bi._predicted_precision_class("Snowflake/snowflake-arctic-embed-s", ["CPUExecutionProvider"]),
                "int8",
            )

    def test_predicted_precision_class_cpu_unregistered_is_full(self):
        # No GPU + a model with NO INT8 source → "full" (fastembed-resident).
        with patch.object(self.bi.accel_embedder, "_available_gpu_providers", return_value=[]):
            self.assertEqual(
                self.bi._predicted_precision_class("Some/unregistered-model", ["CPUExecutionProvider"]),
                "full",
            )

    # --- build-level: re-embed on class change, no re-embed on same class ---

    def _write_meta(self, docs_value: str) -> Path:
        index_dir = self.root / ".wavefoundry" / "index"
        index_dir.mkdir(parents=True, exist_ok=True)
        _seed_meta_store(index_dir, {
                "model_versions": {"docs": docs_value},
                "chunker_versions": {"docs": self.bi._get_chunker().CHUNKER_VERSION},
                "walker_version": self.bi.WALKER_VERSION,
                "content": ["docs"],
                "file_meta": {},
            })
        return index_dir

    def test_explicit_precision_class_change_forces_reembed(self):
        """AC-1: switching a layer's precision class (int8 -> full) forces a full re-embed."""
        _make_repo(self.root, {"docs/guide.md": "## Intro\n\nWave lifecycle docs.\n"})
        # Index recorded as int8; the CURRENT machine predicts "full" (patched) → class change.
        self._write_meta(f"{self.bi.DOCS_MODEL}@int8")
        docs_calls: list[list[str]] = []
        docs_spy = _make_embedder_mock(dim=4, calls=docs_calls)
        with patch.object(self.bi, "_predicted_precision_class", return_value="full"), \
             patch.object(self.bi, "_get_embedder", return_value=docs_spy):
            result = self.bi.build_index(self.root, full=True, content="docs", verbose=False)
        self.assertFalse(result.get("up_to_date", False), "class change must force a rebuild")
        embedded = [t for batch in docs_calls for t in batch]
        self.assertTrue(any("Wave lifecycle" in t for t in embedded), "must re-embed on class change")
        meta = _read_meta_store(self.root / ".wavefoundry" / "index")
        self.assertEqual(
            meta["model_versions"]["docs"],
            f"{self.bi.DOCS_MODEL}@full@{self.bi.EMBEDDING_MODEL_SET_FINGERPRINT}",
        )

    def _make_docs_only_repo(self) -> None:
        # NOTE: deliberately NOT _make_repo — its docs/workflow-config.json drifts on a content=docs
        # second pass (a pre-existing drift-repair quirk unrelated to precision) and would mask the
        # up-to-date assertion. A bare docs file settles cleanly.
        (self.root / "docs").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "guide.md").write_text("## Intro\n\nHello.\n", encoding="utf-8")

    def test_same_precision_class_no_reembed(self):
        """AC-2: a same-class provider/format swap (both "full") does NOT force a re-embed — the
        1p517 FP16<->FP32 interchangeability invariant is preserved."""
        self._make_docs_only_repo()
        docs_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_predicted_precision_class", return_value="full"), \
             patch.object(self.bi, "_get_embedder", return_value=docs_mock):
            self.bi.build_index(self.root, full=True, content="docs", verbose=False)
            # Second pass, SAME predicted class, no file changes → up-to-date (no rebuild, no embed).
            result = self.bi.build_index(self.root, full=False, content="docs", verbose=False)
        self.assertTrue(result.get("up_to_date", False), "same class + no changes must be a no-op")

    def test_legacy_bare_name_index_rebuilds_for_missing_model_set_identity(self):
        """A legacy index lacks artifact provenance and must be re-embedded once."""
        self._make_docs_only_repo()
        docs_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_predicted_precision_class", return_value="full"), \
             patch.object(self.bi, "_get_embedder", return_value=docs_mock):
            self.bi.build_index(self.root, full=True, content="docs", verbose=False)
            _idx = self.root / ".wavefoundry" / "index"
            meta = _read_meta_store(_idx)
            meta["model_versions"]["docs"] = self.bi.DOCS_MODEL  # legacy bare name, no @class
            _seed_meta_store(_idx, meta)
            result = self.bi.build_index(self.root, full=False, content="docs", verbose=False)
        self.assertFalse(result.get("up_to_date", False), "missing model-set identity must rebuild")

    def test_int8_encoding_revision_scopes_reembed_to_int8_layers(self):
        # Wave 1v454 (AC-6/AC-10). Single-row INT8 encoding changed int8 vectors, so an existing
        # int8 index must re-embed exactly once. A full-class index must NOT: the FP graphs carry
        # no quantization ops and their vectors did not move.
        #
        # The obvious implementation -- bumping EMBEDDING_MODEL_SET_FINGERPRINT -- would have
        # re-embedded BOTH layers on every GPU host, because that constant is an all-layer
        # compatibility boundary. This asserts the scoping in both directions, so reverting to the
        # all-layer lever fails here rather than silently costing every GPU operator a full
        # re-embed.
        bare = self.bi.EMBEDDING_MODEL_SET_FINGERPRINT
        self.assertEqual(
            self.bi._identity_fingerprint_for_class("full"),
            bare,
            "a full-class layer must keep the unsuffixed fingerprint, or GPU hosts re-embed",
        )
        int8_fp = self.bi._identity_fingerprint_for_class("int8")
        self.assertNotEqual(
            int8_fp, bare, "an int8 layer must carry a distinct fingerprint, or it never re-embeds"
        )
        self.assertTrue(int8_fp.startswith(f"{bare}-"))
        self.assertIn(self.bi.INT8_ENCODING_REVISION, int8_fp)
        # Round-trips through the parser the compare sites use, for both classes.
        for cls in ("full", "int8"):
            expected = self.bi._identity_fingerprint_for_class(cls)
            self.assertEqual(
                self.bi._model_set_fingerprint_from_version(f"MODEL@{cls}@{expected}"),
                expected,
            )
        # An index recorded under the OLD int8 identity reads as stale against the new one,
        # while a full-class index recorded under the old identity does not.
        self.assertNotEqual(
            self.bi._model_set_fingerprint_from_version(f"MODEL@int8@{bare}"),
            self.bi._identity_fingerprint_for_class("int8"),
        )
        self.assertEqual(
            self.bi._model_set_fingerprint_from_version(f"MODEL@full@{bare}"),
            self.bi._identity_fingerprint_for_class("full"),
        )

    def test_model_set_fingerprint_is_parsed_and_required(self):
        fingerprint = self.bi.EMBEDDING_MODEL_SET_FINGERPRINT
        self.assertEqual(
            self.bi._model_set_fingerprint_from_version(f"MODEL@full@{fingerprint}"),
            fingerprint,
        )
        self.assertEqual(self.bi._model_set_fingerprint_from_version("MODEL@full"), "")


class WalkerVersionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.bi = load_build_index()

    def tearDown(self):
        self.tmp.cleanup()

    def _write_meta(self, extra: dict) -> Path:
        index_dir = self.root / ".wavefoundry" / "index"
        index_dir.mkdir(parents=True, exist_ok=True)
        base = {
            "model_versions": {
                "docs": self.bi.DOCS_MODEL,
                "code": self.bi.CODE_MODEL,
            },
            "chunker_versions": {
                "docs": self.bi._get_chunker().CHUNKER_VERSION,
                "code": self.bi._get_chunker().CHUNKER_VERSION,
            },
            "content": ["docs", "code"],
            "file_meta": {},
        }
        base.update(extra)
        _seed_meta_store(index_dir, base)
        return index_dir

    def test_legacy_index_missing_walker_version_triggers_rebuild(self):
        """An index built before walker versioning has no walker_version key — must rebuild."""
        _make_repo(self.root, {"src/foo.md": "## Guide\n\nContent.\n"})
        self._write_meta({})  # no walker_version key
        docs_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", return_value=docs_mock):
            result = self.bi.build_index(self.root, full=False, content="docs", verbose=False)
        self.assertFalse(result.get("up_to_date", False))
        meta = _read_meta_store(self.root / ".wavefoundry" / "index")
        self.assertEqual(meta["walker_version"], self.bi.WALKER_VERSION)

    def test_stale_walker_version_triggers_rebuild(self):
        """An index with an older walker_version must be fully rebuilt."""
        _make_repo(self.root, {"src/foo.md": "## Guide\n\nContent.\n"})
        self._write_meta({"walker_version": "0"})
        docs_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", return_value=docs_mock):
            result = self.bi.build_index(self.root, full=False, content="docs", verbose=False)
        self.assertFalse(result.get("up_to_date", False))
        meta = _read_meta_store(self.root / ".wavefoundry" / "index")
        self.assertEqual(meta["walker_version"], self.bi.WALKER_VERSION)

    def test_current_walker_version_does_not_force_rebuild(self):
        """An up-to-date walker_version does not contribute to a forced rebuild."""
        _make_repo(self.root, {"src/foo.md": "## Guide\n\nContent.\n"})
        current_wv = self.bi.WALKER_VERSION
        self._write_meta({"walker_version": current_wv})
        docs_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", return_value=docs_mock):
            result = self.bi.build_index(self.root, full=False, content="docs", verbose=False)
        meta = _read_meta_store(self.root / ".wavefoundry" / "index")
        self.assertEqual(meta["walker_version"], current_wv)


class OnnxProviderSelectionTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_build_index()

    def _providers(self, available: list[str]) -> list[str]:
        with patch.object(self.mod.provider_policy, "available_onnx_providers", return_value=tuple(available)):
            with patch.dict(os.environ, {}, clear=True):
                return self.mod._onnx_providers()

    def test_coreml_not_used_on_apple_silicon(self):
        # CoreML is excluded: no-op for INT8 models, actively hurts FP32 models.
        providers = self._providers(["CoreMLExecutionProvider", "CPUExecutionProvider"])
        self.assertNotIn("CoreMLExecutionProvider", providers)
        self.assertIn("CPUExecutionProvider", providers)

    def test_cuda_preferred_when_available(self):
        providers = self._providers(["CUDAExecutionProvider", "CPUExecutionProvider"])
        self.assertEqual(providers[0], "CUDAExecutionProvider")
        self.assertIn("CPUExecutionProvider", providers)

    def test_cpu_only_fallback(self):
        providers = self._providers(["CPUExecutionProvider"])
        self.assertEqual(providers, ["CPUExecutionProvider"])

    def test_cuda_preferred_when_both_cuda_and_coreml_available(self):
        providers = self._providers(["CoreMLExecutionProvider", "CUDAExecutionProvider", "CPUExecutionProvider"])
        self.assertEqual(providers[0], "CUDAExecutionProvider")

    def test_setup_validated_coreml_handoff_is_honored(self):
        with patch.object(
            self.mod.provider_policy,
            "available_onnx_providers",
            return_value=("CoreMLExecutionProvider", "CPUExecutionProvider"),
        ):
            with patch.dict(
                os.environ,
                {"WAVEFOUNDRY_EMBED_PROVIDER_SELECTED": "CoreMLExecutionProvider"},
                clear=True,
            ):
                providers = self.mod._onnx_providers()
        self.assertEqual(providers, ["CoreMLExecutionProvider", "CPUExecutionProvider"])

    def test_onnxruntime_import_error_returns_cpu(self):
        with patch.object(self.mod.provider_policy, "available_onnx_providers", return_value=("CPUExecutionProvider",)):
            result = self.mod._onnx_providers()
        self.assertEqual(result, ["CPUExecutionProvider"])


# ---------------------------------------------------------------------------
# _make_vector_rows null-normalization tests (12qmp-bug)
# ---------------------------------------------------------------------------

class MakeLanceRowsNullNormalizationTests(unittest.TestCase):
    """AC-1 / AC-2: None language/section are normalized to '' before LanceDB write."""

    def setUp(self):
        self.mod = load_build_index()

    def _make_vec(self, dim=4):
        import numpy as np
        return np.zeros(dim, dtype=np.float32)

    def _call(self, chunk):
        import numpy as np
        vecs = np.zeros((1, 4), dtype=np.float32)
        return self.mod._make_vector_rows([chunk], vecs)[0]

    def test_language_none_normalized_to_empty_string(self):
        """AC-1: language=None in chunk dict produces row['language']==''."""
        chunk = {"text": "hello", "path": "docs/a.md", "kind": "doc", "language": None, "section": "Intro"}
        row = self._call(chunk)
        self.assertEqual(row["language"], "")

    def test_section_none_normalized_to_empty_string(self):
        """AC-2: section=None in chunk dict produces row['section']==''."""
        chunk = {"text": "hello", "path": "docs/a.md", "kind": "doc", "language": "markdown", "section": None}
        row = self._call(chunk)
        self.assertEqual(row["section"], "")

    def test_both_none_normalized(self):
        """Both language and section None in same chunk are both normalized."""
        chunk = {"text": "hello", "path": "docs/a.md", "kind": "doc", "language": None, "section": None}
        row = self._call(chunk)
        self.assertEqual(row["language"], "")
        self.assertEqual(row["section"], "")

    def test_non_none_values_preserved(self):
        """Non-None language/section values are not modified."""
        chunk = {"text": "fn foo()", "path": "src/a.py", "kind": "function", "language": "python", "section": "auth"}
        row = self._call(chunk)
        self.assertEqual(row["language"], "python")
        self.assertEqual(row["section"], "auth")

    def test_original_chunk_not_mutated(self):
        """_make_vector_rows must not mutate the input chunk dict."""
        chunk = {"text": "x", "path": "a.md", "kind": "doc", "language": None, "section": None}
        self._call(chunk)
        self.assertIsNone(chunk["language"])
        self.assertIsNone(chunk["section"])


class PlanLanceDeltaRowsTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_build_index()

    def _chunk(self, chunk_id: str, text: str) -> dict:
        return {"id": chunk_id, "text": text, "path": "src/a.py", "kind": "function"}

    def test_missing_chunk_hash_key_forces_full_rebuild(self):
        existing = [{"id": "c1", "text": "old"}]  # no chunk_hash key
        new_chunks = [self._chunk("c1", "new")]
        delete_ids, rows_to_add, fallback_required, stats = self.mod._plan_vector_delta_rows(
            existing_rows=existing,
            new_chunks=new_chunks,
            embedder=_make_embedder_mock(),
            label="project",
        )
        self.assertTrue(fallback_required)
        self.assertEqual(delete_ids, set())
        self.assertEqual(rows_to_add, [])

    def test_empty_chunk_hash_value_forces_full_rebuild(self):
        existing = [{"id": "c1", "text": "old", "chunk_hash": "   "}]  # present but blank
        new_chunks = [self._chunk("c1", "new")]
        delete_ids, rows_to_add, fallback_required, stats = self.mod._plan_vector_delta_rows(
            existing_rows=existing,
            new_chunks=new_chunks,
            embedder=_make_embedder_mock(),
            label="project",
        )
        self.assertTrue(fallback_required)

    def test_distinct_unicode_java_owner_ids_survive_delta_planning(self):
        # Wave 1shv4 final-review P1: the supported Java fallback previously gave
        # `A` and `A` + combining acute the same initializer id. `_plan_vector_delta_rows`
        # keys by id, so that collision silently reduced two source chunks to one row.
        chunker = self.mod._get_chunker()
        accented = "A\u0301"
        source = (
            'class A { static { R.put("plain", "PlainOwnerZz"); } }\n'
            f'class {accented} {{ static {{ R.put("accented", "AccentOwnerZz"); }} }}\n'
        )
        with patch.object(chunker, "_ts_parse", return_value=None):
            emitted = chunker.chunk_java(source, "src/Collision.java")
        new_chunks = [
            dict(vars(chunk)) for chunk in emitted
            if "__static_init_" in chunk.id or "__instance_init_" in chunk.id
        ]
        expected = {
            "src/Collision.java::A.__static_init_1__",
            f"src/Collision.java::{accented}.__static_init_1__",
        }
        self.assertEqual({chunk["id"] for chunk in new_chunks}, expected)
        self.assertEqual(len(new_chunks), 2)

        _delete_ids, rows, fallback_required, stats = self.mod._plan_vector_delta_rows(
            existing_rows=[],
            new_chunks=new_chunks,
            embedder=_make_embedder_mock(),
            label="project",
        )
        self.assertFalse(fallback_required)
        self.assertEqual({row["id"] for row in rows}, expected)
        self.assertEqual(stats["written"], 2)

    def test_partial_java_tree_unicode_owners_survive_delta_planning(self):
        # The tree path used to return partial success for this file: the ordinary class
        # survived, while javac-legal single-character Sc/Pc owners were ERROR+sibling-body
        # shapes and never reached the fallback. Pin the real public dispatch and planner.
        chunker = self.mod._get_chunker()
        source = (
            'class A { static { R.put("a", "PlainZz"); } }\n'
            'class € { static { R.put("e", "CurrencyZz"); } }\n'
            'class ‿ { static { R.put("p", "ConnectorZz"); } }\n'
        )
        path = "src/SingleUnicode.java"
        emitted = chunker.chunk_file(source, path)
        new_chunks = [
            dict(vars(chunk)) for chunk in emitted
            if "__static_init_" in chunk.id or "__instance_init_" in chunk.id
        ]
        expected = {
            f"{path}::A.__static_init_1__",
            f"{path}::€.__static_init_1__",
            f"{path}::‿.__static_init_1__",
        }
        self.assertEqual({chunk["id"] for chunk in new_chunks}, expected)
        self.assertEqual(len(new_chunks), 3)

        _delete_ids, rows, fallback_required, stats = self.mod._plan_vector_delta_rows(
            existing_rows=[],
            new_chunks=new_chunks,
            embedder=_make_embedder_mock(),
            label="project",
        )
        self.assertFalse(fallback_required)
        self.assertEqual({row["id"] for row in rows}, expected)
        self.assertEqual(stats["written"], 3)

    def test_unchanged_chunk_set_is_a_no_op_with_zero_embeds(self):
        # 1wngv AC-4/AC-9 (wave 1wpif): an incremental pass over an unchanged
        # chunk set is provably equivalent to the full build state — zero
        # deletes, zero adds, zero embedding calls; every chunk is accounted
        # unchanged. Unaffected unique chunks therefore retain stable ids.
        chunks = [self._chunk(f"c{i}", f"text {i}") for i in range(4)]
        existing = []
        for chunk in chunks:
            row = dict(chunk)
            row["chunk_hash"] = self.mod._chunk_hash(chunk)
            row["vector"] = [0.0, 0.0, 0.0, 0.0]
            existing.append(row)
        calls: list[list[str]] = []
        delete_ids, rows_to_add, fallback_required, stats = self.mod._plan_vector_delta_rows(
            existing_rows=existing,
            new_chunks=[dict(c) for c in chunks],
            embedder=_make_embedder_mock(calls=calls),
            label="project",
        )
        self.assertFalse(fallback_required)
        self.assertEqual(delete_ids, set())
        self.assertEqual(rows_to_add, [])
        self.assertEqual(stats, {"written": 0, "removed": 0, "unchanged": 4})
        self.assertEqual(calls, [], "no embedding call may run for an unchanged set")

    def test_single_changed_chunk_embeds_exactly_once(self):
        # 1wngv AC-4/AC-9: changing ONE chunk re-embeds exactly that chunk;
        # the other ids stay untouched (no delete, no re-add, no embed).
        chunks = [self._chunk(f"c{i}", f"text {i}") for i in range(4)]
        existing = []
        for chunk in chunks:
            row = dict(chunk)
            row["chunk_hash"] = self.mod._chunk_hash(chunk)
            row["vector"] = [0.0, 0.0, 0.0, 0.0]
            existing.append(row)
        changed = [dict(c) for c in chunks]
        changed[2]["text"] = "text 2 EDITED"
        calls: list[list[str]] = []
        delete_ids, rows_to_add, fallback_required, stats = self.mod._plan_vector_delta_rows(
            existing_rows=existing,
            new_chunks=changed,
            embedder=_make_embedder_mock(calls=calls),
            label="project",
        )
        self.assertFalse(fallback_required)
        self.assertEqual(delete_ids, {"c2"})
        self.assertEqual([row["id"] for row in rows_to_add], ["c2"])
        self.assertEqual(stats, {"written": 1, "removed": 1, "unchanged": 3})
        self.assertEqual(sum(len(batch) for batch in calls), 1,
                         "exactly one chunk may be embedded")


# ---------------------------------------------------------------------------
# Wave 1p3b9 (1p399): drift detection between file_meta and Lance
# ---------------------------------------------------------------------------

class LanceDriftDetectionTests(unittest.TestCase):
    """AC-1, AC-2, AC-7, AC-8: `_detect_vector_drift` returns the file_meta
    paths that have zero rows in any Lance table — those are "drifted" and
    must be re-chunked even when file_meta hash matches.

    Tests use mocked Lance access since the surface is set-difference logic;
    full end-to-end is covered by the incremental-build tests when run with
    LanceDB available in the tool venv."""

    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _make_db_with_paths(self, table_to_paths):
        return table_to_paths

    @contextmanager
    def _native_paths(self, tables):
        import index_state_store as iss
        index_dir=self.root/'index'
        store=iss.IndexStateStore(index_dir)
        try:
            for layer,paths in tables.items():
                with store._conn:
                    iss._apply_chunk_deltas_locked(store,layer,add_rows=[
                        {'id':str(i),'path':path,'text':path,'vector':[1.0]+[0.0]*383} for i,path in enumerate(sorted(paths))])
            yield
        finally:
            store.close()

    def _index_dir_with_tables(self, table_names):
        import index_state_store as iss
        index_dir=self.root/'index'
        store=iss.IndexStateStore(index_dir);store.close()
        return index_dir

    def _as_meta(self, paths, chunks_emitted=None):
        """Build the dict shape `_detect_vector_drift` expects (wave 1p3iw).
        Empty dict per entry means `chunks_emitted` is absent → falls through
        to the drift check unchanged (legacy / first-pass behavior).
        Pass `chunks_emitted=0` (or a mapping) to test the skip behavior."""
        if chunks_emitted is None:
            return {p: {} for p in paths}
        if isinstance(chunks_emitted, dict):
            return {p: ({"chunks_emitted": chunks_emitted[p]} if p in chunks_emitted else {}) for p in paths}
        # Scalar — apply to every path
        return {p: {"chunks_emitted": chunks_emitted} for p in paths}

    def test_returns_empty_when_file_meta_empty(self):
        result = self.bi._detect_vector_drift(
            self.root, {}, chunk_eligible_rel_paths={"docs/a.md"}, verbose=False,
        )
        self.assertEqual(result, set())

    def test_returns_empty_when_no_lance_tables_present(self):
        # No `.lance` dirs at index_dir → fresh layer, no drift
        result = self.bi._detect_vector_drift(
            self.root,
            self._as_meta({"docs/a.md"}),
            chunk_eligible_rel_paths={"docs/a.md"},
            verbose=False,
        )
        self.assertEqual(result, set())

    def test_detects_drift_when_path_missing_from_lance(self):
        """AC-1, AC-2: a path claimed by file_meta but absent from Lance is
        returned as drifted."""
        from unittest.mock import patch
        index_dir = self._index_dir_with_tables({"docs"})
        db = self._make_db_with_paths({"docs": {"docs/present.md"}})
        with self._native_paths(db):
            result = self.bi._detect_vector_drift(
                index_dir,
                self._as_meta({"docs/present.md", "docs/drifted.md"}),
                chunk_eligible_rel_paths={"docs/present.md", "docs/drifted.md"},
                verbose=False,
            )
        self.assertEqual(result, {"docs/drifted.md"})

    def test_no_drift_when_file_meta_and_lance_agree(self):
        """AC-5, AC-8 (happy path): when every file_meta path has Lance rows,
        return empty set; the incremental skip-on-hash-match optimization is
        preserved unchanged."""
        from unittest.mock import patch
        index_dir = self._index_dir_with_tables({"docs", "code"})
        db = self._make_db_with_paths({
            "docs": {"docs/a.md", "docs/b.md"},
            "code": {"src/foo.py"},
        })
        with self._native_paths(db):
            result = self.bi._detect_vector_drift(
                index_dir,
                self._as_meta({"docs/a.md", "docs/b.md", "src/foo.py"}),
                chunk_eligible_rel_paths={"docs/a.md", "docs/b.md", "src/foo.py"},
                verbose=False,
            )
        self.assertEqual(result, set())

    def test_drift_detection_unions_across_tables(self):
        """AC-3: a file_meta path counts as "indexed" if it appears in ANY
        Lance table (docs OR code). A path in both file_meta and either Lance
        table is not drifted."""
        from unittest.mock import patch
        index_dir = self._index_dir_with_tables({"docs", "code"})
        db = self._make_db_with_paths({
            "docs": {"docs/a.md"},
            "code": {"src/foo.py"},
        })
        with self._native_paths(db):
            result = self.bi._detect_vector_drift(
                index_dir,
                self._as_meta({"docs/a.md", "src/foo.py", "docs/missing.md"}),
                chunk_eligible_rel_paths={"docs/a.md", "src/foo.py", "docs/missing.md"},
                verbose=False,
            )
        self.assertEqual(result, {"docs/missing.md"})

    def test_native_open_failure_preserves_source_and_surfaces(self):
        index_dir=self._index_dir_with_tables({'docs'})
        import index_state_store as iss
        with patch.object(self.bi,'_get_index_state_store',return_value=iss), patch.object(iss,'open_read_only',side_effect=OSError('disk unavailable')):
            with self.assertRaises(OSError):
                self.bi._detect_vector_drift(index_dir,self._as_meta({'docs/a.md'}),
                    chunk_eligible_rel_paths={'docs/a.md'})

    # --- Wave 1p3iw: chunks_emitted skip behavior ---

    def test_excludes_path_with_chunks_emitted_zero(self):
        """AC-2 (1p3iw): a path with explicit ``chunks_emitted == 0`` in its
        file_meta entry is excluded from the drift check — the prior run
        recorded that this file legitimately produces zero chunks, so its
        absence from Lance is expected, not drift."""
        from unittest.mock import patch
        index_dir = self._index_dir_with_tables({"docs"})
        db = self._make_db_with_paths({"docs": {"docs/present.md"}})
        file_meta = {
            "docs/present.md": {},
            "docs/empty.md": {"chunks_emitted": 0},
        }
        with self._native_paths(db):
            result = self.bi._detect_vector_drift(
                index_dir, file_meta,
                chunk_eligible_rel_paths=set(file_meta), verbose=False,
            )
        self.assertEqual(result, set())

    def test_includes_path_with_chunks_emitted_field_absent(self):
        """AC-3 (1p3iw): a path with no ``chunks_emitted`` field (legacy
        meta.json, or fresh stat-mismatch entry from `_detect_changes`) falls
        through to the drift check unchanged — one repair attempt learns the
        true count. (1rmaf narrowing guard: the eligibility set INCLUDES the
        zero-row path, so the flag here is attributable to the field logic —
        an over-broad eligibility exclusion would turn this test red.)"""
        from unittest.mock import patch
        index_dir = self._index_dir_with_tables({"docs"})
        db = self._make_db_with_paths({"docs": {"docs/present.md"}})
        file_meta = {
            "docs/present.md": {},
            "docs/legacy-missing.md": {},  # No chunks_emitted field
        }
        with self._native_paths(db):
            result = self.bi._detect_vector_drift(
                index_dir, file_meta,
                chunk_eligible_rel_paths=set(file_meta), verbose=False,
            )
        self.assertEqual(result, {"docs/legacy-missing.md"})

    def test_includes_path_with_chunks_emitted_positive_but_lance_missing(self):
        """AC-4 (1p3iw): a path with ``chunks_emitted > 0`` recorded but
        absent from Lance is real drift — the indexer believed it emitted N
        chunks last time, Lance has 0 rows for it now. Must converge by
        re-chunk + re-embed. (1rmaf narrowing guard: the zero-row path is in
        the eligibility set, so positive-field drift on ELIGIBLE paths must
        keep repairing — the 1p3b9 contract narrows only by eligibility.)"""
        from unittest.mock import patch
        index_dir = self._index_dir_with_tables({"docs"})
        db = self._make_db_with_paths({"docs": {"docs/present.md"}})
        file_meta = {
            "docs/present.md": {"chunks_emitted": 3},
            "docs/real-drift.md": {"chunks_emitted": 5},
        }
        with self._native_paths(db):
            result = self.bi._detect_vector_drift(
                index_dir, file_meta,
                chunk_eligible_rel_paths=set(file_meta), verbose=False,
            )
        self.assertEqual(result, {"docs/real-drift.md"})

    def test_thrash_regression_zero_chunk_file_skipped_on_subsequent_updates(self):
        """AC-7 (1p3iw): the thrash regression — a file with `chunks_emitted=0`
        is NOT returned as drifted, even when called repeatedly. This is the
        observable contract that distinguishes the fix from the prior
        behavior. On pre-fix code: every call returned the path. On post-fix:
        no call does."""
        from unittest.mock import patch
        index_dir = self._index_dir_with_tables({"docs"})
        db = self._make_db_with_paths({"docs": set()})  # Lance has zero rows
        file_meta = {"docs/legitimately-empty.md": {"chunks_emitted": 0}}
        eligible = set(file_meta)
        with self._native_paths(db):
            r1 = self.bi._detect_vector_drift(
                index_dir, file_meta, chunk_eligible_rel_paths=eligible, verbose=False)
            r2 = self.bi._detect_vector_drift(
                index_dir, file_meta, chunk_eligible_rel_paths=eligible, verbose=False)
            r3 = self.bi._detect_vector_drift(
                index_dir, file_meta, chunk_eligible_rel_paths=eligible, verbose=False)
        self.assertEqual(r1, set())
        self.assertEqual(r2, set())
        self.assertEqual(r3, set())

    def test_chunks_for_file_returns_empty_on_empty_input(self):
        """AC-5 (1p3iw) — data path for the chunks_emitted population: an
        empty source produces no doc and no code chunks. The build_index
        loop computes `len(dc) + len(cc) == 0` and persists that as
        chunks_emitted=0, which the next-update drift check uses to skip."""
        dc, cc = self.bi._chunks_for_file("docs/empty.md", "")
        self.assertEqual(dc, [])
        self.assertEqual(cc, [])

    def test_chunks_for_file_returns_empty_on_marker_region_only_content(self):
        """AC-5 (1p3jc): renderer-owned marker-region-only files produce no
        semantic chunks, so chunks_emitted remains 0 and drift detection skips
        them on subsequent updates."""
        source = "<!-- wave:agent-surface begin -->\nGenerated\n<!-- wave:agent-surface end -->\n"
        dc, cc = self.bi._chunks_for_file("src/generated.py", source)
        self.assertEqual(dc, [])
        self.assertEqual(cc, [])

    def test_chunks_for_file_returns_nonempty_on_real_content(self):
        """AC-5 (1p3iw) — the contrapositive: a normal markdown file emits
        chunks; chunks_emitted would be > 0."""
        dc, cc = self.bi._chunks_for_file(
            "docs/sample.md",
            "# Title\n\nThis is a test paragraph with enough content to chunk.\n",
        )
        self.assertGreaterEqual(len(dc) + len(cc), 1)

    # --- 1rmaf: chunk-eligibility gate (drift candidacy scoped to files_for_content) ---

    def test_excludes_chunk_ineligible_path_field_absent(self):
        """1rmaf AC-1 (helper level): a meta-tracked, zero-row path with NO
        ``chunks_emitted`` field is NOT flagged when it lies outside the
        current build's chunk-eligible set — the repair path could never
        reach it, so flagging it would loop forever (the live defect)."""
        from unittest.mock import patch
        index_dir = self._index_dir_with_tables({"docs"})
        db = self._make_db_with_paths({"docs": {"docs/present.md"}})
        file_meta = {
            "docs/present.md": {},
            ".wavefoundry/framework/scripts/tests/test_x.py": {},  # excluded upstream
        }
        with self._native_paths(db):
            result = self.bi._detect_vector_drift(
                index_dir, file_meta,
                chunk_eligible_rel_paths={"docs/present.md"}, verbose=False,
            )
        self.assertEqual(result, set())

    def test_excludes_chunk_ineligible_path_stale_positive_field(self):
        """1rmaf Req-2: an ineligible zero-row path carrying a STALE POSITIVE
        ``chunks_emitted`` (recorded under earlier include flags) is likewise
        not flagged — eligibility, not the recorded count, is the primary
        gate."""
        from unittest.mock import patch
        index_dir = self._index_dir_with_tables({"docs", "code"})
        db = self._make_db_with_paths({"docs": {"docs/present.md"}, "code": set()})
        file_meta = {
            "docs/present.md": {},
            "tests/test_helper.py": {"chunks_emitted": 99},  # stale positive, now excluded
        }
        with self._native_paths(db):
            result = self.bi._detect_vector_drift(
                index_dir, file_meta,
                chunk_eligible_rel_paths={"docs/present.md"}, verbose=False,
            )
        self.assertEqual(result, set())

    def test_eligible_zero_row_path_still_flagged_alongside_ineligible_skip(self):
        """1rmaf AC-2 guard: the eligibility gate must narrow, not weaken —
        an ELIGIBLE zero-row path is still flagged in the same call that
        skips an ineligible one."""
        from unittest.mock import patch
        index_dir = self._index_dir_with_tables({"docs"})
        db = self._make_db_with_paths({"docs": {"docs/present.md"}})
        file_meta = {
            "docs/present.md": {},
            "docs/drifted.md": {},
            ".wavefoundry/framework/scripts/tests/test_x.py": {},
        }
        with self._native_paths(db):
            result = self.bi._detect_vector_drift(
                index_dir, file_meta,
                chunk_eligible_rel_paths={"docs/present.md", "docs/drifted.md"},
                verbose=False,
            )
        self.assertEqual(result, {"docs/drifted.md"})

    def test_verbose_logs_ineligible_skip_count_with_reason(self):
        """1rmaf AC-5 (log shape): when verbose, the ineligible-skip count is
        logged WITH the reason, distinguishable from genuine drift repairs."""
        from unittest.mock import patch
        index_dir = self._index_dir_with_tables({"docs"})
        db = self._make_db_with_paths({"docs": {"docs/present.md"}})
        file_meta = {
            "docs/present.md": {},
            ".wavefoundry/framework/scripts/tests/test_x.py": {},
        }
        out = io.StringIO()
        with self._native_paths(db), \
                contextlib.redirect_stdout(out):
            result = self.bi._detect_vector_drift(
                index_dir, file_meta,
                chunk_eligible_rel_paths={"docs/present.md"}, verbose=True,
            )
        self.assertEqual(result, set())
        self.assertIn(
            "drift-detect skipped 1 path(s) as chunk-ineligible "
            "(outside this build's content filters)",
            out.getvalue(),
        )

    def test_verbose_no_ineligible_line_when_all_paths_eligible(self):
        """1rmaf AC-5 (log shape, contrapositive): no ineligible-skip line
        when every meta path is chunk-eligible — quiet logs stay quiet."""
        from unittest.mock import patch
        index_dir = self._index_dir_with_tables({"docs"})
        db = self._make_db_with_paths({"docs": {"docs/present.md"}})
        file_meta = {"docs/present.md": {}}
        out = io.StringIO()
        with self._native_paths(db), \
                contextlib.redirect_stdout(out):
            self.bi._detect_vector_drift(
                index_dir, file_meta,
                chunk_eligible_rel_paths={"docs/present.md"}, verbose=True,
            )
        self.assertNotIn("chunk-ineligible", out.getvalue())


class SQLiteDriftDetectionScaleTests(unittest.TestCase):
    setUp = LanceDriftDetectionTests.setUp
    tearDown = LanceDriftDetectionTests.tearDown
    _native_paths = LanceDriftDetectionTests._native_paths
    _index_dir_with_tables = LanceDriftDetectionTests._index_dir_with_tables
    _as_meta = LanceDriftDetectionTests._as_meta
    def _scale(self,count):
        import time
        paths={f'src/p{i}.py' for i in range(count)}
        index_dir=self._index_dir_with_tables({'code'})
        with self._native_paths({'code':paths}):
            start=time.monotonic()
            result=self.bi._detect_vector_drift(index_dir,self._as_meta(paths | {'src/missing.py'}),
                chunk_eligible_rel_paths=paths | {'src/missing.py'})
            elapsed=time.monotonic()-start
        self.assertEqual(result,{'src/missing.py'})
        from perf_budget_policy import assert_operation_within_budget
        assert_operation_within_budget(self, "100K-row drift detection", elapsed)
    def test_10k_rows_sub_second(self): self._scale(10000)
    def test_100k_rows_contention_safe_budget(self): self._scale(100000)


class LanceDriftEligibilityBuildTests(unittest.TestCase):
    """1rmaf: end-to-end drift-eligibility behavior through ``build_index``.

    The live defect: ``meta.json`` tracks the full walked set but
    ``chunks_emitted`` is only ever recorded for files that pass the content
    filters, so a meta-tracked, chunking-excluded, zero-row file was drift-
    flagged on EVERY incremental build — a non-converging repair loop that
    nullified the zero-change fast path. Fixtures mirror the live shape:
    a ``.wavefoundry/framework/scripts`` file made meta-trackable via the
    workflow-config code prefix but chunk-INELIGIBLE in docs mode (the
    post-edit hook's default content mode, where the live loop manifested).
    """

    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _make_docs_mode_repo(self) -> str:
        """Repo where a framework-script file is meta-tracked (docs+code
        graph surface) but outside the docs content walk (under the
        ``.wavefoundry/`` blanket exclusion, not in the docs include set).
        Returns the excluded file's rel path."""
        (self.root / "docs").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "workflow-config.json").write_text(
            json.dumps({
                "lifecycle_id_policy": {"epoch_utc": "2020-02-02T02:02:00Z", "hour_offset": 0},
                "indexing": {
                    "project_include_prefixes": {
                        "docs": [],
                        "code": [".wavefoundry/framework/scripts"],
                    },
                },
            }),
            encoding="utf-8",
        )
        (self.root / "docs" / "guide.md").write_text(
            "## Intro\n\nEnough real content to emit at least one docs chunk.\n",
            encoding="utf-8",
        )
        util = self.root / ".wavefoundry" / "framework" / "scripts" / "util.py"
        util.parent.mkdir(parents=True, exist_ok=True)
        util.write_text("def util():\n    return 1\n", encoding="utf-8")
        return ".wavefoundry/framework/scripts/util.py"

    def _build(self, *, full=False, content="docs", include_tests=False, verbose=False):
        """Run build_index with a mocked embedder; returns (result, stderr, stdout)."""
        err, out = io.StringIO(), io.StringIO()
        with patch.object(self.bi, "_get_embedder", return_value=_make_embedder_mock(dim=4)), \
                redirect_stderr(err), contextlib.redirect_stdout(out):
            result = self.bi.build_index(
                self.root, full=full, content=content,
                include_tests=include_tests, verbose=verbose,
            )
        return result, err.getvalue(), out.getvalue()

    def _meta(self) -> dict:
        return _read_meta_store(self.root / ".wavefoundry" / "index")

    def _neutralize_per_kind_residual(self) -> None:
        """Pin ``docs/workflow-config.json``'s ``chunks_emitted`` to 0 after a
        docs-only full build. The file emits only code-KIND chunks, so a
        docs-only build records a positive count while writing zero rows —
        the per-kind residual the change doc names as deferred out-of-scope
        (it would otherwise be drift-flagged here and drown the assertions).
        On the live repo the equivalent files have code-table rows from
        all-mode setup; pinning the field keeps these fixtures focused on
        the ELIGIBILITY defect under test."""
        index_dir = self.root / ".wavefoundry" / "index"
        meta = self._meta()
        entry = meta["file_meta"].get("docs/workflow-config.json")
        if entry is not None:
            entry["chunks_emitted"] = 0
            _seed_meta_store(index_dir, meta)

    def test_ac1_docs_mode_excluded_zero_row_file_field_absent_never_flagged(self):
        """AC-1 (field absent): meta-tracked + chunking-excluded + zero rows →
        zero drift flags across two consecutive incremental docs builds."""
        rel = self._make_docs_mode_repo()
        self._build(full=True, content="docs")
        file_meta = self._meta().get("file_meta", {})
        # Fixture validity: meta-tracked, never chunked (field absent) — the
        # exact live-loop state. A self-healing fixture would prove nothing.
        self.assertIn(rel, file_meta)
        self.assertNotIn("chunks_emitted", file_meta[rel])
        self._neutralize_per_kind_residual()
        for i in (1, 2):
            result, err, _ = self._build(full=False, content="docs")
            self.assertNotIn("repairing", err,
                f"incremental build {i} drift-flagged the chunk-ineligible file:\n{err}")
            self.assertTrue(result.get("up_to_date"),
                f"incremental build {i} should be a no-op")

    def test_ac1_docs_mode_excluded_zero_row_file_stale_positive_never_flagged(self):
        """AC-1 (stale positive): the same excluded file carrying a stale
        positive ``chunks_emitted`` (recorded under earlier include flags) is
        likewise never flagged — eligibility is the primary gate."""
        rel = self._make_docs_mode_repo()
        self._build(full=True, content="docs")
        self._neutralize_per_kind_residual()
        index_dir = self.root / ".wavefoundry" / "index"
        meta = self._meta()
        meta["file_meta"][rel]["chunks_emitted"] = 7  # stale positive
        _seed_meta_store(index_dir, meta)
        for i in (1, 2):
            result, err, _ = self._build(full=False, content="docs")
            self.assertNotIn("repairing", err,
                f"incremental build {i} drift-flagged the stale-positive excluded file:\n{err}")
            self.assertTrue(result.get("up_to_date"))

    def test_ac2_eligible_zero_row_file_still_repaired_then_quiet(self):
        """AC-2 guard: a chunk-ELIGIBLE file with zero Lance rows is still
        drift-flagged and repaired; the repair records ``chunks_emitted`` and
        the next build is quiet."""
        self._make_docs_mode_repo()
        self._build(full=True, content="docs")
        self._neutralize_per_kind_residual()
        index_dir = self.root / ".wavefoundry" / "index"
        # Simulate real drift: rows vanish for an eligible docs file.
        import sqlite_runtime
        conn = sqlite_runtime.connect(index_paths.runtime_database_path(index_dir))
        try:
            conn.execute("DELETE FROM vectors_docs WHERE chunk_id IN (SELECT id FROM chunks_docs WHERE path=?)", ("docs/guide.md",))
        finally:
            conn.close()
        result, err, _ = self._build(full=False, content="docs")
        self.assertIn("repairing 1 drifted file(s)", err)
        self.assertIn("docs/guide.md", err)
        rows = _read_index_chunks(index_dir, "docs")
        self.assertIn("docs/guide.md", {r.get("path") for r in rows},
            "repair must restore the eligible file's rows")
        self.assertGreater(
            self._meta()["file_meta"]["docs/guide.md"].get("chunks_emitted", 0), 0)
        result2, err2, _ = self._build(full=False, content="docs")
        self.assertNotIn("repairing", err2, "repaired file must converge")
        self.assertTrue(result2.get("up_to_date"))

    def test_ac3_include_tests_flip_makes_excluded_file_eligible_flagged_repaired(self):
        """AC-3 (code mode, ``_is_test_code_path`` class): with the flag off
        the test file is never flagged; flipping ``--include-tests`` on makes
        it eligible → flagged → repaired; the next build is quiet. Eligibility
        is computed per build from the current filters, never persisted."""
        _make_repo(self.root, {
            "src/foo.py": "def foo():\n    return 1\n",
            "tests/test_helper.py": "def test_helper():\n    assert 1 + 1 == 2\n",
        })
        rel = "tests/test_helper.py"
        self._build(full=True, content="code", include_tests=False)
        file_meta = self._meta().get("file_meta", {})
        # Fixture validity: meta-tracked, excluded by the flag-sensitive
        # layer (NOT the unconditional framework-test carve-out), zero rows.
        self.assertIn(rel, file_meta)
        self.assertNotIn("chunks_emitted", file_meta[rel])
        result, err, _ = self._build(full=False, content="code", include_tests=False)
        self.assertNotIn("repairing", err,
            f"flag off: excluded test file must not be drift-flagged:\n{err}")
        result, err, _ = self._build(full=False, content="code", include_tests=True)
        self.assertIn("repairing 1 drifted file(s)", err,
            f"flag on: newly eligible zero-row file must be flagged:\n{err}")
        self.assertIn(rel, err)
        meta_after = self._meta()["file_meta"][rel]
        self.assertGreater(meta_after.get("chunks_emitted", 0), 0,
            "repair must record the true chunk count")
        rows = _read_index_chunks(self.root / ".wavefoundry" / "index", "code")
        self.assertIn(rel, {r.get("path") for r in rows})
        result, err, _ = self._build(full=False, content="code", include_tests=True)
        self.assertNotIn("repairing", err, "repaired file must converge")
        self.assertTrue(result.get("up_to_date"))

    def test_ac6_graph_only_incremental_performs_no_drift_detection(self):
        """AC-6 (write-capability guard, Req-7): a ``content="graph"``
        incremental build never calls ``_detect_vector_drift`` — in that mode
        ``files_for_content`` is the UNFILTERED code walk while zero semantic
        rows are writable, so any eligibility intersection would be a no-op
        and the loop would survive."""
        self._make_docs_mode_repo()
        self._build(full=True, content="docs")
        calls: list = []
        def spy(*args, **kwargs):
            calls.append((args, kwargs))
            return set()
        err = io.StringIO()
        with patch.object(self.bi, "_detect_vector_drift", side_effect=spy), \
                redirect_stderr(err):
            self.bi.build_index(self.root, full=False, content="graph", verbose=False)
        self.assertEqual(calls, [], "graph-only build must skip drift detection outright")
        self.assertNotIn("repairing", err.getvalue())

    def test_ac6_graph_only_incremental_no_repair_log_and_verbose_reason(self):
        """AC-6 (unpatched) + AC-5: the real graph-only incremental flags
        nothing — the "repairing N drifted file(s)" stderr line is ABSENT
        even with a meta-tracked zero-row file present — and the verbose skip
        line states the REASON so quiet builds are distinguishable from
        no-drift builds in field logs."""
        rel = self._make_docs_mode_repo()
        self._build(full=True, content="docs")
        self.assertNotIn("chunks_emitted", self._meta()["file_meta"][rel])
        err, out = io.StringIO(), io.StringIO()
        with redirect_stderr(err), contextlib.redirect_stdout(out):
            self.bi.build_index(self.root, full=False, content="graph", verbose=True)
        self.assertNotIn("repairing", err.getvalue())
        self.assertIn("no semantic writes this build", out.getvalue())

    def test_idle_reap_still_receives_wide_meta_union(self):
        """1rmaf security tripwire (Req-8): the idle-path
        ``_reap_stranded_vector_rows`` call still receives the WIDE meta union
        — including chunk-INELIGIBLE paths — never the narrow eligibility
        set. The zero-change fast path is the common path post-fix; a set
        mix-up here would be high-frequency destructive (a docs-only run
        would reap every code-table row)."""
        rel = self._make_docs_mode_repo()
        self._build(full=True, content="docs")
        self._neutralize_per_kind_residual()
        captured: dict = {}
        def fake_reap(db_path, eligible_paths, **kwargs):
            captured["eligible_paths"] = set(eligible_paths)
            return {"total": 0}
        err = io.StringIO()
        with patch.object(self.bi, "_reap_stranded_vector_rows", side_effect=fake_reap), \
                patch.object(self.bi, "_get_embedder", return_value=_make_embedder_mock(dim=4)), \
                redirect_stderr(err):
            result = self.bi.build_index(self.root, full=False, content="docs", verbose=False)
        self.assertTrue(result.get("up_to_date"))
        self.assertIn("eligible_paths", captured, "idle reap must run on the fast path")
        self.assertEqual(captured["eligible_paths"], set(self._meta()["file_meta"].keys()))
        self.assertIn(rel, captured["eligible_paths"],
            "the chunk-INELIGIBLE path must stay in the reaper's wide union")


class OversizedFileGuardTests(unittest.TestCase):
    """Wave 1p5c4: walk_repo drops files over the hard size cap so a multi-GB blob (e.g. a SQL
    backup) is never read or tree-sitter-parsed."""

    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "docs").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _write_config(self, indexing: dict) -> None:
        (self.root / "docs" / "workflow-config.json").write_text(
            json.dumps({"indexing": indexing}), encoding="utf-8")

    def test_walk_repo_skips_oversized_files(self):
        self._write_config({"max_file_bytes": 50})
        (self.root / "small.md").write_text("hi\n", encoding="utf-8")
        (self.root / "big.md").write_text("x" * 500, encoding="utf-8")
        rels = {str(f.relative_to(self.root)).replace("\\", "/") for f in self.bi.walk_repo(self.root)}
        self.assertIn("small.md", rels)
        self.assertNotIn("big.md", rels)

    def test_walk_repo_keeps_all_when_cap_disabled(self):
        self._write_config({"max_file_bytes": 0})  # 0 = no cap
        (self.root / "big.md").write_text("x" * 500, encoding="utf-8")
        rels = {str(f.relative_to(self.root)).replace("\\", "/") for f in self.bi.walk_repo(self.root)}
        self.assertIn("big.md", rels)

    def test_default_cap_keeps_normal_files(self):
        # No override → generous default (5 MB); ordinary source/docs are unaffected.
        (self.root / "code.py").write_text("def f():\n    return 1\n", encoding="utf-8")
        rels = {str(f.relative_to(self.root)).replace("\\", "/") for f in self.bi.walk_repo(self.root)}
        self.assertIn("code.py", rels)

    def test_walk_repo_prunes_gitignored_directories(self):
        # Wave 1p5c4: a gitignored directory (e.g. the LanceDB index dir) must never be walked —
        # we should not even stat the files inside it.
        (self.root / ".gitignore").write_text("ignored_index/\n", encoding="utf-8")
        (self.root / "ignored_index").mkdir()
        (self.root / "ignored_index" / "shard.md").write_text("data\n", encoding="utf-8")
        (self.root / "kept.md").write_text("# Kept\n", encoding="utf-8")
        rels = {str(f.relative_to(self.root)).replace("\\", "/") for f in self.bi.walk_repo(self.root)}
        self.assertIn("kept.md", rels)
        self.assertFalse(any(r.startswith("ignored_index/") for r in rels),
                         f"gitignored dir should not be walked; got {rels}")


class CorpusExclusionCensusTests(unittest.TestCase):
    """Wave 1wfsl (1wfsn): executed-census pins for the consolidated exclusion story.

    Every candidate name's classification is pinned at MECHANISM-CLASS granularity
    (name / extension-or-sniff / corpus-filter / machine-authority path) by running
    the REAL walk and corpus filter over a constructed fixture tree — the census
    that planned this change ran the same way (never grep; two grep censuses in
    wave 1wfsl were falsified against the tree). All three retrieval corpora
    (semantic docs, semantic code + lexical, graph) derive from this one walk."""

    # (relative path, is_binary) — mirrors the committed census fixture
    # (docs/waves/ evidence census_exclusions.py).
    NAME_LAYER = ["package-lock.json", "yarn.lock", "pnpm-lock.yaml",
                  "prompt-surface-manifest.json", "npm-shrinkwrap.json",
                  "packages.lock.json"]
    SUFFIX_LAYER = ["app.min.js", "styles.min.css"]
    EXTENSION_LAYER = ["Cargo.lock", "poetry.lock", "uv.lock", "Pipfile.lock",
                       "composer.lock", "Gemfile.lock", "flake.lock"]
    SNIFF_LAYER = ["bun.lockb"]
    # 1wl7v (wave 1wl7w): diagram.excalidraw and pipeline.drawio LEFT this
    # layer (label extraction re-admitted both extensions); .snap remains the
    # layer's pinned member so the census and hatch pins stay non-vacuous.
    GENERATED_EXT_LAYER = ["ui-state.snap"]
    CORPUS_FILTERED = ["go.sum", "gradle.lockfile", "app.js.map"]
    MACHINE_AUTHORITY = ["docs/scan-findings.json"]
    LEGITIMATE_SIBLINGS = ["package.json", "app.js", "styles.css"]

    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _write_fixture(self):
        text_files = {}
        for rel in (self.NAME_LAYER + self.SUFFIX_LAYER + self.EXTENSION_LAYER
                    + self.GENERATED_EXT_LAYER + self.CORPUS_FILTERED
                    + self.MACHINE_AUTHORITY + self.LEGITIMATE_SIBLINGS):
            text_files[rel] = "generated: true\ncontent: sample\n"
        text_files["app.js"] = "var a = 1;\n"
        text_files["styles.css"] = ".a { color: #fff; }\n"
        _make_repo(self.root, text_files)
        for rel in self.SNIFF_LAYER:
            (self.root / rel).write_bytes(b"\x00\x01binary-lockb\x00")

    def _reinclude_config(self, names: list[str]) -> None:
        (self.root / "docs" / "workflow-config.json").write_text(
            json.dumps({"indexing": {"walk_reinclude_filenames": names}}),
            encoding="utf-8",
        )

    def _walk_rels(self) -> set[str]:
        return {str(f.relative_to(self.root)).replace("\\", "/")
                for f in self.bi.walk_repo(self.root)}

    def test_census_classifications_pinned_per_mechanism_class(self):
        self._write_fixture()
        rels = self._walk_rels()
        for rel in (self.NAME_LAYER + self.SUFFIX_LAYER + self.EXTENSION_LAYER
                    + self.SNIFF_LAYER + self.GENERATED_EXT_LAYER
                    + self.MACHINE_AUTHORITY):
            self.assertNotIn(rel, rels, f"{rel} must be walk-excluded")
        for rel in self.CORPUS_FILTERED + self.LEGITIMATE_SIBLINGS:
            self.assertIn(rel, rels, f"{rel} must walk")
        # Mechanism-class pins: name layer entries are in the name constants,
        # extension layer in BINARY_EXTENSIONS, generated in the generated set.
        for rel in self.NAME_LAYER:
            self.assertIn(rel, self.bi.HARDCODED_EXCLUDE_FILENAMES)
        for rel in self.SUFFIX_LAYER:
            self.assertTrue(rel.endswith(tuple(self.bi.HARDCODED_EXCLUDE_FILENAME_SUFFIXES)))
        for rel in self.EXTENSION_LAYER:
            self.assertIn("." + rel.rsplit(".", 1)[-1].lower(), self.bi.BINARY_EXTENSIONS)
        for rel in self.GENERATED_EXT_LAYER:
            self.assertIn("." + rel.rsplit(".", 1)[-1].lower(), self.bi._GENERATED_EXCLUDE_EXTENSIONS)
        # Corpus-filter class: walks, but the code corpus drops it.
        corpus = {str(f.relative_to(self.root)).replace("\\", "/")
                  for f in self.bi._filter_code_files(
                      self.bi.walk_repo(self.root), self.root,
                      include_tests=False, include_generated=False)}
        for rel in self.CORPUS_FILTERED:
            self.assertNotIn(rel, corpus, f"{rel} must be corpus-filtered")
        for rel in ["package.json", "app.js", "styles.css"]:
            self.assertIn(rel, corpus, f"{rel} must stay in the code corpus")

    def test_reinclude_hatch_restores_name_layer_only(self):
        self._write_fixture()
        self._reinclude_config(["package-lock.json", "app.min.js"])
        rels = self._walk_rels()
        self.assertIn("package-lock.json", rels)   # exact-name subtraction
        self.assertIn("app.min.js", rels)          # suffix-pattern subtraction
        self.assertNotIn("styles.min.css", rels)   # un-listed suffix stays excluded
        self.assertNotIn("npm-shrinkwrap.json", rels)

    def test_reinclude_hatch_cannot_override_extension_or_sniff(self):
        self._write_fixture()
        self._reinclude_config(["Cargo.lock", "bun.lockb", "yarn.lock",
                                "ui-state.snap"])
        rels = self._walk_rels()
        self.assertNotIn("Cargo.lock", rels)   # .lock binary extension holds
        self.assertNotIn("bun.lockb", rels)    # content sniff holds
        # yarn.lock is the documented double-coverage case: the name subtraction
        # applies, but the .lock binary extension still excludes it.
        self.assertNotIn("yarn.lock", rels)
        self.assertNotIn("ui-state.snap", rels)  # generated extension holds
        # (1wl7v: pipeline.drawio left this pin when the extension left the
        # generated layer — it walks by default now, no hatch needed.)

    def test_reinclude_hatch_cannot_resurrect_machine_authority_paths(self):
        self._write_fixture()
        (self.root / "docs" / "waves" / "1abcd test-wave").mkdir(parents=True)
        (self.root / "docs" / "waves" / "1abcd test-wave" / "events.jsonl").write_text(
            '{"record_type":"executable_evidence"}\n', encoding="utf-8")
        self._reinclude_config(["events.jsonl", "scan-findings.json",
                                "docs/scan-findings.json"])
        rels = self._walk_rels()
        self.assertNotIn("docs/waves/1abcd test-wave/events.jsonl", rels,
                         "canonical wave ledger must never be re-includable")
        self.assertNotIn("docs/scan-findings.json", rels,
                         "secret-scan findings ledger must never be re-includable")
        # Path-shaped entries are rejected by the resolver outright.
        self.assertNotIn(
            "docs/scan-findings.json",
            self.bi._resolve_walk_reinclude_filenames(self.root),
        )

    def test_files_seam_enforces_scan_findings_boundary(self):
        # The ``files=`` incremental seam bypasses walk_repo; the machine-authority
        # family (including the scan-findings ledger) is re-enforced there.
        self._write_fixture()
        filtered = self.bi._filter_secret_scan_findings(
            [self.root / "docs" / "scan-findings.json", self.root / "package.json"],
            self.root,
        )
        rels = {str(p.relative_to(self.root)).replace("\\", "/") for p in filtered}
        self.assertEqual(rels, {"package.json"})

    def test_walker_version_bumped_for_filter_logic_change(self):
        self.assertGreaterEqual(int(self.bi.WALKER_VERSION), 12)

    def test_rst_adoc_walk_and_docs_layer_membership(self):
        # Wave 1wfsl (1wfsm): rst/adoc/asciidoc walk as known text and their
        # section chunks are doc-kind, which the kind-based layer routing
        # (_is_docs_kind) carries into the docs layer. WALKER_VERSION 13 rides
        # the filter-logic clause for the known-text registration.
        for ext in (".rst", ".adoc", ".asciidoc"):
            self.assertIn(ext, self.bi._KNOWN_TEXT_EXTENSIONS)
        self.assertGreaterEqual(int(self.bi.WALKER_VERSION), 13)
        _make_repo(self.root, {
            "docs/guide.rst": "Guide\n=====\n\nSec\n---\n\nSection prose.\n",
            "docs/guide.adoc": "= Guide\n\n== Sec\n\nSection prose.\n",
            "docs/guide.asciidoc": "= Guide\n\n== Sec\n\nSection prose.\n",
        })
        rels = {str(f.relative_to(self.root)).replace("\\", "/")
                for f in self.bi.walk_repo(self.root)}
        for rel in ("docs/guide.rst", "docs/guide.adoc", "docs/guide.asciidoc"):
            self.assertIn(rel, rels, f"{rel} must walk")
        import chunker as chunker_mod
        for rel in ("docs/guide.rst", "docs/guide.adoc"):
            chunks = chunker_mod.chunk_file(
                (self.root / rel).read_text(encoding="utf-8"), rel)
            doc_kinds = [c for c in chunks if self.bi._is_docs_kind(c.kind)]
            self.assertTrue(doc_kinds, f"{rel} must emit doc-kind chunks")

    def test_secret_scanner_candidates_not_narrowed(self):
        # AC-3: the standalone scanner's candidate set (all tracked files) is
        # independent of the walk exclusions — a walk-excluded straggler MUST
        # still be a scan candidate.
        self._write_fixture()
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        for cmd in (["git", "init", "-q"], ["git", "add", "-A"],
                    ["git", "commit", "-qm", "fixture"]):
            subprocess.run(cmd, cwd=self.root, env=env, check=True,
                           capture_output=True)
        sys.path.insert(0, str(SCRIPTS_ROOT))
        try:
            from wave_lint_lib.secrets_validators import get_scan_files
        finally:
            sys.path.pop(0)
        candidates = {str(p.relative_to(self.root)).replace("\\", "/")
                      for p in get_scan_files(self.root, True)}
        for rel in ["npm-shrinkwrap.json", "app.min.js", "package-lock.json",
                    "docs/scan-findings.json"]:
            self.assertIn(rel, candidates,
                          f"{rel} must remain a secret-scan candidate")
        _rmtree_git(self.root / ".git")  # Windows-safe tempdir cleanup


class StreamingRebuildParityTests(unittest.TestCase):
    """Wave 1p5ch: the streamed full-rebuild table must be row-identical regardless of buffer size.
    Feeding every chunk in one `add()` IS the batch write (a single create_table with all rows), so
    'one big add' vs 'tiny buffer, many flushes' is the streaming-vs-batch parity check — using only
    the production `_StreamingLayerWriter`, with no separate reference implementation to drift."""

    def setUp(self):
        self.bi = load_build_index()

    def _fake_embedder(self):
        return _make_embedder_mock()

    def _chunks(self, n):
        return [
            {"id": f"f{i}.py::sym{i}", "path": f"f{i}.py", "kind": "code", "language": "python",
             "section": f"sym{i}", "lines": [1, 2], "text": f"def sym{i}(): return {i}"}
            for i in range(n)
        ]

    def test_streamed_table_is_buffer_invariant(self):
        import sqlite_vector_store as vectors
        import index_state_store as iss
        chunks=self._chunks(25)
        outputs=[]
        for batch_size in (25,3):
            with tempfile.TemporaryDirectory() as temp, vectors.PreparedUpdates(Path(temp)) as prepared:
                index_dir=Path(temp)
                writer=self.bi._StreamingLayerWriter(prepared,'code',self._fake_embedder(),'code')
                for start in range(0,len(chunks),batch_size):
                    writer.add(chunks[start:start+batch_size])
                writer.finalize()
                store=iss.IndexStateStore(index_dir)
                try:
                    with store._conn: prepared.apply(store)
                finally: store.close()
                outputs.append({r['id']:r for r in vectors.payload_rows(index_dir,'code',include_vector=True)})
        self.assertEqual(outputs[0],outputs[1])
        self.assertEqual(len(outputs[0]),25)

    def test_resolve_embed_buffer_chunks_override_and_floor(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            # Honors a sane override.
            (root / "docs" / "workflow-config.json").write_text(
                json.dumps({"indexing": {"embed_buffer_chunks": 5000}}), encoding="utf-8")
            self.assertEqual(self.bi._resolve_embed_buffer_chunks(root), 5000)
            # Floors at EMBED_BATCH_SIZE so GPU batches stay full.
            (root / "docs" / "workflow-config.json").write_text(
                json.dumps({"indexing": {"embed_buffer_chunks": 1}}), encoding="utf-8")
            self.assertEqual(self.bi._resolve_embed_buffer_chunks(root), self.bi.EMBED_BATCH_SIZE)
            # Default when unset.
            (root / "docs" / "workflow-config.json").write_text("{}", encoding="utf-8")
            self.assertEqual(self.bi._resolve_embed_buffer_chunks(root), self.bi.EMBED_BUFFER_CHUNKS_DEFAULT)
            # 1p7it: the unset default is pinned to 1024 — best build throughput in the on-machine
            # benchmark (peak RSS is buffer-invariant, so this is purely a throughput choice).
            self.assertEqual(self.bi.EMBED_BUFFER_CHUNKS_DEFAULT, 1024)

    def test_resolve_embed_batch_size_per_model_and_global(self):
        # Per-layer forward-batch width stays independently overridable even when docs and code
        # currently select the same model; smaller batch = less CPU activation memory.
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            cfg = root / "docs" / "workflow-config.json"
            DOCS, CODE = self.bi.DOCS_MODEL, self.bi.CODE_MODEL
            # Unset → per-model default, pinned to 32 (the lowest-memory + fastest CPU batch).
            cfg.write_text("{}", encoding="utf-8")
            self.assertEqual(self.bi._DEFAULT_EMBED_BATCH, 32)
            self.assertEqual(self.bi._resolve_embed_batch_size(DOCS, root, layer="docs"), 32)
            self.assertEqual(self.bi._resolve_embed_batch_size(CODE, root, layer="code"), 32)
            # Global override applies to both models.
            cfg.write_text(json.dumps({"indexing": {"embed_batch_size": 64}}), encoding="utf-8")
            self.assertEqual(self.bi._resolve_embed_batch_size(DOCS, root, layer="docs"), 64)
            self.assertEqual(self.bi._resolve_embed_batch_size(CODE, root, layer="code"), 64)
            # Per-model override wins over the global and is independent per model.
            cfg.write_text(json.dumps({"indexing": {
                "embed_batch_size": 64, "code_embed_batch_size": 32, "docs_embed_batch_size": 128}}),
                encoding="utf-8")
            self.assertEqual(self.bi._resolve_embed_batch_size(CODE, root, layer="code"), 32)
            self.assertEqual(self.bi._resolve_embed_batch_size(DOCS, root, layer="docs"), 128)
            # Invalid (non-positive) falls through to the default.
            cfg.write_text(json.dumps({"indexing": {"code_embed_batch_size": 0}}), encoding="utf-8")
            self.assertEqual(self.bi._resolve_embed_batch_size(CODE, root, layer="code"), 32)

    def test_streaming_rebuild_bounds_buffer_and_reports_file_progress(self):
        """AC-1 (memory bound) + AC-4 (file-oriented progress): driving the real
        `_run_streaming_full_rebuild` over many files with a tiny buffer, no single
        embed batch may approach the corpus size — each is bounded by
        ``buffer_chunks + max(per-file chunks)`` — and progress is logged as
        ``indexed file N/M files`` with no total-chunk pre-count."""
        import tempfile, io, contextlib, re
        import unittest.mock as mock

        import sqlite_vector_store as vectors
        import index_state_store as iss
        buffer_chunks = 4
        n_files = 14
        with tempfile.TemporaryDirectory() as tmp, vectors.PreparedUpdates(Path(tmp) / "lance") as prepared:
            root = Path(tmp)
            files = []
            for i in range(n_files):
                p = root / f"mod{i}.py"
                # Two functions per file → a couple of code chunks each.
                p.write_text(
                    f"def alpha{i}(x):\n    return x + {i}\n\n\ndef beta{i}(y):\n    return y * {i}\n",
                    encoding="utf-8",
                )
                files.append(p)

            db_path = root / "lance"
            chunks_emitted = {}
            sizes = []  # length of every batch handed to the writer (== peak resident buffer at flush)
            orig_add = self.bi._StreamingLayerWriter.add

            def spy_add(writer_self, chunks):
                sizes.append(len(chunks))
                return orig_add(writer_self, chunks)

            out = io.StringIO()
            with mock.patch.object(self.bi._StreamingLayerWriter, "add", spy_add), \
                    contextlib.redirect_stdout(out):
                self.bi._run_streaming_full_rebuild(
                    db_path=db_path,
                    files_to_index=files,
                    root=root,
                    build_docs=False,
                    build_code=True,
                    docs_embedder=None,
                    code_embedder=self._fake_embedder(),
                    chunks_emitted_by_file=chunks_emitted,
                    buffer_chunks=buffer_chunks,
                    verbose=False,
                    docs_elapsed=[],
                    code_elapsed=[],
                    prepared=prepared,
                )
            log = out.getvalue()

            store=iss.IndexStateStore(db_path)
            try:
                with store._conn: prepared.apply(store)
            finally: store.close()
            total_code = vectors.layer_counts(db_path)['code']

            # AC-1: streamed, not one big write — multiple flushes, and every batch is
            # bounded by the buffer plus a single file's chunk count (corpus-independent).
            self.assertGreaterEqual(len(sizes), 2, "expected multiple flushes (streaming)")
            self.assertEqual(sum(sizes), total_code, "every chunk must be written exactly once")
            max_file_chunks = max(chunks_emitted.values())
            self.assertLessEqual(
                max(sizes), buffer_chunks + max_file_chunks,
                "peak resident buffer must stay bounded by buffer + one file's chunks",
            )
            self.assertLess(max(sizes), total_code, "no single batch may hold the whole corpus")

            # AC-4: file-oriented progress, terminating at N/N, with no total-chunk pre-count.
            self.assertRegex(log, r"indexed file \d+/%d files" % n_files)
            self.assertIn("indexed file %d/%d files" % (n_files, n_files), log)
            self.assertNotIn("/%d code chunks" % total_code, log)
            self.assertNotRegex(log, r"chunks \d+[–-]\d+/\d+")


class StorageRebuildSourceTests(unittest.TestCase):
    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_strict_census_rejects_unreadable_directory_even_without_prior_rows(self):
        def denied(root, **kwargs):
            kwargs["unreadable_dirs"].add("src")
            return []
        with patch.object(self.bi, "walk_repo", side_effect=denied):
            with self.assertRaisesRegex(RuntimeError, "storage_rebuild_source_unreadable"):
                self.bi.preflight_rebuild_sources(self.root)

    def test_strict_census_hashes_current_sources_and_allows_empty_layers(self):
        self.assertEqual(self.bi.preflight_rebuild_sources(self.root), {"docs": {}, "code": {}})
        (self.root / "guide.md").write_text("# Source\nCurrent text")
        before = self.bi.preflight_rebuild_sources(self.root)
        (self.root / "guide.md").write_text("# Changed")
        self.assertNotEqual(before, self.bi.preflight_rebuild_sources(self.root))

    def test_full_rebuild_read_failure_is_fatal_when_receipt_owned(self):
        missing = self.root / "missing.py"
        with self.assertRaises(FileNotFoundError):
            self.bi._run_streaming_full_rebuild(db_path=self.root, files_to_index=[missing],
                root=self.root, build_docs=False, build_code=False, docs_embedder=None,
                code_embedder=None, chunks_emitted_by_file={}, buffer_chunks=10,
                verbose=False, docs_elapsed=[], code_elapsed=[], strict_reads=True)


class CachedFirstEmbedderTests(unittest.TestCase):
    """Wave 1p5cx: the reindex path must load fastembed models from the local HF cache first
    (``local_files_only=True``, no network / no unauthenticated-request warning) and fall back to an
    online download only on a genuine cache miss."""

    def setUp(self):
        self.bi = load_build_index()
        self.bi._EMBEDDER_CACHE.clear()

    def test_cached_first_returns_offline_construct_when_present(self):
        calls = []

        def fake_cls(model_name, providers, local_files_only=False):
            calls.append(local_files_only)
            return f"embedder::{model_name}::lfo={local_files_only}"

        emb = self.bi._text_embedding_cached_first(fake_cls, "m", ["CPUExecutionProvider"])
        self.assertEqual(emb, "embedder::m::lfo=True")
        self.assertEqual(calls, [True], "no online attempt when the cached load succeeds")

    def test_cached_first_falls_back_to_online_on_cache_miss(self):
        calls = []

        def fake_cls(model_name, providers, local_files_only=False):
            calls.append(local_files_only)
            if local_files_only:
                raise RuntimeError("LocalEntryNotFound (simulated cold cache)")
            return f"online::{model_name}"

        emb = self.bi._text_embedding_cached_first(fake_cls, "m", ["CPUExecutionProvider"])
        self.assertEqual(emb, "online::m")
        self.assertEqual(calls, [True, False], "cached-first, then online download fallback")

    def test_get_embedder_uses_cached_first_on_fastembed_path(self):
        seen = []

        class FakeTE:
            def __init__(self, model_name, providers, local_files_only=False):
                seen.append(local_files_only)
                self.model_name = model_name

        # Force the fastembed branch: no accel embedder.
        with patch.object(self.bi, "accel_embedder", None), \
                patch.object(self.bi, "_onnx_providers", return_value=["CPUExecutionProvider"]), \
                patch.dict("sys.modules", {"fastembed": types.SimpleNamespace(TextEmbedding=FakeTE)}):
            emb = self.bi._get_embedder("Snowflake/snowflake-arctic-embed-s")
        self.assertIsInstance(emb, FakeTE)
        self.assertEqual(seen, [True], "fastembed path loads cached-first (local_files_only=True)")


class IncrementalGpuRoutingTests(unittest.TestCase):
    """Wave 1p938: a build run smaller than one full GPU batch (INCREMENTAL_GPU_MIN_CHUNKS) is
    routed to the full-precision CPU fastembed path on a GPU machine, skipping the 32x512 GPU
    accel session's pad-waste. No effect on a CPU-bound machine."""

    def setUp(self):
        self.bi = load_build_index()
        self.bi._EMBEDDER_CACHE.clear()

    def _patch_fastembed(self):
        # Returns a context that forces the fastembed branch to a known sentinel + records the load.
        seen = []

        class FakeTE:
            def __init__(self, model_name, providers, local_files_only=False):
                seen.append(local_files_only)
                self.model_name = model_name
                self.provider = "fastembed-cpu-full"

        return FakeTE, seen

    def test_equal_selectors_preselect_one_bulk_instance_for_mixed_boundary(self):
        sentinel = object()
        threshold = self.bi.INCREMENTAL_GPU_MIN_CHUNKS
        with patch.object(self.bi, "_get_embedder", return_value=sentinel) as get:
            docs, code = self.bi._resolve_build_embedders(
                build_docs=True,
                build_code=True,
                full=False,
                docs_chunk_count=threshold - 1,
                code_chunk_count=threshold,
            )
        self.assertIs(docs, sentinel)
        self.assertIs(code, docs)
        get.assert_called_once_with(self.bi.DOCS_MODEL, n_chunks=threshold)

    def test_equal_selectors_share_one_small_run_instance(self):
        sentinel = object()
        with patch.object(self.bi, "_get_embedder", return_value=sentinel) as get:
            docs, code = self.bi._resolve_build_embedders(
                build_docs=True,
                build_code=True,
                full=False,
                docs_chunk_count=2,
                code_chunk_count=3,
            )
        self.assertIs(docs, code)
        get.assert_called_once_with(self.bi.DOCS_MODEL, n_chunks=3)

    def test_divergent_selectors_resolve_independently(self):
        with patch.object(self.bi, "DOCS_MODEL", "supplier/docs"), patch.object(
            self.bi, "CODE_MODEL", "supplier/code"
        ), patch.object(
            self.bi, "_get_embedder", side_effect=lambda name, n_chunks: object()
        ) as get:
            docs, code = self.bi._resolve_build_embedders(
                build_docs=True,
                build_code=True,
                full=False,
                docs_chunk_count=2,
                code_chunk_count=7,
            )
        self.assertIsNot(docs, code)
        self.assertEqual(
            get.call_args_list,
            [call("supplier/docs", n_chunks=2), call("supplier/code", n_chunks=7)],
        )

    def test_small_run_on_gpu_machine_uses_cpu_fastembed(self):
        # AC-1 / AC-4: GPU available + n_chunks below threshold → CPU fastembed (full precision),
        # make_embedder (the GPU accel session) is NOT constructed.
        FakeTE, seen = self._patch_fastembed()
        with patch.object(self.bi, "_onnx_providers", return_value=["CoreMLExecutionProvider"]), \
             patch.object(self.bi.accel_embedder, "make_embedder") as mk, \
             patch.dict("sys.modules", {"fastembed": types.SimpleNamespace(TextEmbedding=FakeTE)}):
            emb = self.bi._get_embedder("Snowflake/snowflake-arctic-embed-s", n_chunks=3)
        self.assertIsInstance(emb, FakeTE)
        mk.assert_not_called()
        self.assertEqual(seen, [True], "small run loads fastembed cached-first (full precision)")

    def test_bulk_run_on_gpu_machine_uses_accel(self):
        # AC-2: GPU available + n_chunks at/above threshold → the GPU accel embedder is used
        # unchanged (no small-run CPU detour).
        accel_sentinel = MagicMock()
        accel_sentinel.provider = "CoreMLExecutionProvider"
        with patch.object(self.bi, "_onnx_providers", return_value=["CoreMLExecutionProvider"]), \
             patch.object(self.bi.accel_embedder, "make_embedder", return_value=accel_sentinel) as mk:
            emb = self.bi._get_embedder("Snowflake/snowflake-arctic-embed-s",
                                        n_chunks=self.bi.INCREMENTAL_GPU_MIN_CHUNKS)
        self.assertIs(emb, accel_sentinel)
        mk.assert_called_once()

    def test_cpu_bound_machine_small_run_unchanged(self):
        # AC-3: no GPU → the small-run detour never triggers (no GPU session to skip); make_embedder
        # is still called (it would resolve the INT8-CPU embedder in production).
        accel_sentinel = MagicMock()
        accel_sentinel.provider = "CPUExecutionProvider"
        with patch.object(self.bi, "_onnx_providers", return_value=["CPUExecutionProvider"]), \
             patch.object(self.bi.accel_embedder, "_available_gpu_providers", return_value=[]), \
             patch.object(self.bi.accel_embedder, "make_embedder", return_value=accel_sentinel) as mk:
            emb = self.bi._get_embedder("Snowflake/snowflake-arctic-embed-s", n_chunks=3)
        self.assertIs(emb, accel_sentinel, "CPU-bound machine: small run still uses the resolved embedder")
        mk.assert_called_once()

    def test_no_n_chunks_hint_uses_accel(self):
        # A caller that omits n_chunks (e.g. a full build) never takes the small-run detour.
        accel_sentinel = MagicMock()
        accel_sentinel.provider = "CoreMLExecutionProvider"
        with patch.object(self.bi, "_onnx_providers", return_value=["CoreMLExecutionProvider"]), \
             patch.object(self.bi.accel_embedder, "make_embedder", return_value=accel_sentinel) as mk:
            emb = self.bi._get_embedder("Snowflake/snowflake-arctic-embed-s")  # no n_chunks
        self.assertIs(emb, accel_sentinel)
        mk.assert_called_once()

    def test_small_run_cpu_path_is_full_precision_class(self):
        # AC-4: the small-run CPU path on a GPU machine stays in the "full" precision class (cos 1.0
        # with the FP16 index), so it composes with 1p936 as a no-op — no precision-class change,
        # no spurious re-embed. A GPU machine always predicts "full" for the model.
        self.assertEqual(
            self.bi._predicted_precision_class("Snowflake/snowflake-arctic-embed-s", ["CoreMLExecutionProvider"]),
            "full",
        )

    def test_threshold_default_is_static_batch(self):
        # The default threshold is one full GPU batch (accel_embedder.STATIC_BATCH), so a bulk/full
        # build (>= one batch) uses GPU and only genuinely small incremental runs go to CPU.
        self.assertEqual(self.bi.INCREMENTAL_GPU_MIN_CHUNKS, self.bi.accel_embedder.STATIC_BATCH)

    def test_full_rebuild_never_passes_small_n_chunks(self):
        """Regression (found by a real full rebuild): the streaming full-rebuild path produces
        chunks AFTER the embedder is loaded, so ``new_doc_chunks`` is still empty at load time.
        A full build must pass ``n_chunks=None`` (bulk → GPU), NOT ``len()==0`` — else a full
        rebuild of the entire corpus would be misrouted to the CPU fastembed path."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "docs").mkdir(parents=True)
        (root / "docs" / "guide.md").write_text("## Intro\n\nHello docs.\n", encoding="utf-8")
        (root / "src").mkdir(parents=True)
        (root / "src" / "foo.py").write_text("def f():\n    return 1\n", encoding="utf-8")
        seen = []

        def spy(model, n_chunks=None):
            seen.append((model, n_chunks))
            return _make_embedder_mock(dim=4)

        with patch.object(self.bi, "_get_embedder", side_effect=spy):
            self.bi.build_index(root, full=True, content="all", verbose=False)
        self.assertTrue(seen, "a full build must load at least one embedder")
        for model, n in seen:
            self.assertIsNone(n, f"full rebuild must pass n_chunks=None, got {n!r} for {model}")


class ContentScopeFreshnessTests(unittest.TestCase):
    """Wave 1sc7c (1sek8): per-layer change detection, corpus unification,
    hook coverage, and the heal path for the content-scope staleness cluster."""

    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.index_dir = self.root / ".wavefoundry" / "index"

    def _build(self, content: str = "all", full: bool = False, **kw) -> dict:
        docs_mock = _make_embedder_mock(dim=4)
        code_mock = _make_embedder_mock(dim=4)

        def _emb(model, n_chunks=None):
            return docs_mock if model == self.bi.DOCS_MODEL else code_mock
        with patch.object(self.bi, "_get_embedder", side_effect=_emb):
            with contextlib.redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                return self.bi.build_index(self.root, full=full, content=content, verbose=False, **kw)

    def _code_paths(self) -> set:
        return {r["path"] for r in _read_index_chunks(self.index_dir, "code")}

    def _code_texts(self) -> str:
        return "\n".join(r.get("text") or "" for r in _read_index_chunks(self.index_dir, "code"))

    def test_poison_scenario_docs_build_cannot_freeze_code_layer(self):
        # AC-1: the exact field sequence — code + docs edits interleaved, the
        # docs build runs first (the hook's historic behavior), then a code
        # build. Pre-1sek8 the docs build stamped the code file's fresh hash
        # and the code build said "up to date" forever.
        _make_repo(self.root, {
            "src/app.py": "def alpha():\n    return 1\n",
            "docs/guide.md": "## Guide\n\nOriginal.\n",
        })
        self._build(full=True)
        (self.root / "src" / "app.py").write_text(
            "def alpha():\n    return 'freshness_sentinel_token'\n", encoding="utf-8")
        (self.root / "docs" / "guide.md").write_text("## Guide\n\nEdited.\n", encoding="utf-8")
        self._build(content="docs")
        self.assertNotIn("freshness_sentinel_token", self._code_texts())  # docs build didn't touch code
        result = self._build(content="code")
        self.assertFalse(result.get("up_to_date", False))
        self.assertIn("freshness_sentinel_token", self._code_texts())

    def test_dual_output_file_coherent_under_content_all(self):
        # A .py edit updates BOTH its code chunks and its docstring doc chunks
        # in one automatic-path (content=all) build.
        _make_repo(self.root, {
            "src/mod.py": '"""Module doc original."""\n\ndef f():\n    return 1\n',
        })
        self._build(full=True)
        (self.root / "src" / "mod.py").write_text(
            '"""Module doc updated_sentinel."""\n\ndef f():\n    return "code_updated_sentinel"\n',
            encoding="utf-8")
        self._build(content="all")
        docs_text = "\n".join(r.get("text") or "" for r in _read_index_chunks(self.index_dir, "docs"))
        self.assertIn("updated_sentinel", docs_text)
        self.assertIn("code_updated_sentinel", self._code_texts())

    def test_scoped_build_leaves_other_layer_queued_not_erased(self):
        # A code-only build after a dual-output edit updates the code table
        # and leaves the DOCS layer stale-but-queued: the next docs build
        # picks the docstring change up.
        _make_repo(self.root, {
            "src/mod.py": '"""Doc one."""\n\ndef f():\n    return 1\n',
            "docs/guide.md": "## G\n\nBody.\n",
        })
        self._build(full=True)
        (self.root / "src" / "mod.py").write_text(
            '"""Doc two_sentinel."""\n\ndef f():\n    return "two_code_sentinel"\n', encoding="utf-8")
        self._build(content="code")
        self.assertIn("two_code_sentinel", self._code_texts())
        docs_text = "\n".join(r.get("text") or "" for r in _read_index_chunks(self.index_dir, "docs"))
        self.assertNotIn("two_sentinel", docs_text)  # docs layer not built yet
        self._build(content="docs")
        docs_text = "\n".join(r.get("text") or "" for r in _read_index_chunks(self.index_dir, "docs"))
        self.assertIn("two_sentinel", docs_text)  # ...and not erased, queued

    def test_corpus_membership_identical_across_content_scopes(self):
        # AC-3: content=all and content=code agree — tests/generated excluded
        # under both (unless --include-tests), extensionless code names kept.
        files = {
            "src/foo.py": "def f(): pass\n",
            "tests/test_foo.py": "def test_f(): pass\n",
            "Jenkinsfile": "stage one\n" * 30,
        }
        _make_repo(self.root, files)
        self._build(content="all", full=True)
        all_paths = self._code_paths()
        import shutil
        shutil.rmtree(self.index_dir)
        self._build(content="code", full=True)
        code_paths = self._code_paths()
        self.assertEqual(all_paths, code_paths)
        self.assertIn("src/foo.py", all_paths)
        self.assertIn("Jenkinsfile", all_paths)
        self.assertNotIn("tests/test_foo.py", all_paths)
        shutil.rmtree(self.index_dir)
        self._build(content="all", full=True, include_tests=True)
        self.assertIn("tests/test_foo.py", self._code_paths())

    def test_empty_layer_state_heals_poisoned_repo(self):
        # The migration IS the heal: a pre-1sek8 repo arrives with hash-current
        # meta, stale Lance content, and NO layer state (the v5 bump reset the
        # store) — the first build re-chunks everything eligible and converges.
        _make_repo(self.root, {"src/app.py": "def f():\n    return 'old_content'\n"})
        self._build(full=True)
        # Simulate the poisoned arrival: newer file content, meta stamped
        # current (as a pre-fix docs build would have done), layer state absent.
        (self.root / "src" / "app.py").write_text(
            "def f():\n    return 'healed_content_sentinel'\n", encoding="utf-8")
        meta = _read_meta_store(self.index_dir)
        import hashlib as _h
        fresh = (self.root / "src" / "app.py").read_bytes()
        entry = meta["file_meta"]["src/app.py"]
        entry["hash"] = _h.sha256(fresh).hexdigest()
        st = (self.root / "src" / "app.py").stat()
        entry["mtime"] = st.st_mtime; entry["size"] = st.st_size
        entry["inode"] = getattr(st, "st_ino", 0)
        _seed_meta_store(self.index_dir, meta)
        # Wipe layer state (what a schema-bump reset / pre-1sek8 store looks like).
        import sqlite3 as _sq
        con = _sq.connect(index_paths.runtime_database_path(self.index_dir))
        with con:
            con.execute("DELETE FROM layer_path_state")
        con.close()
        self.assertNotIn("healed_content_sentinel", self._code_texts())
        result = self._build(content="code")
        self.assertFalse(result.get("up_to_date", False))
        self.assertIn("healed_content_sentinel", self._code_texts())

    def test_healthy_zero_change_build_keeps_fast_exit(self):
        # No perpetual churn: with layer state populated, a zero-change build
        # (ineligible test files present) takes the up-to-date fast path.
        _make_repo(self.root, {
            "src/foo.py": "def f(): pass\n",
            "tests/test_foo.py": "def test_f(): pass\n",
        })
        self._build(full=True)
        self._build(content="all")  # first incremental populates nothing new
        result = self._build(content="all")
        self.assertTrue(result.get("up_to_date", False))

    def test_corpus_narrowing_reap_cleans_layer_state_and_logs(self):
        # Migration reap: a code table carrying test-file rows (the old
        # content=all corpus) gets them reaped on the next default build,
        # loudly (store log) — and the layer state follows, so re-widening
        # via --include-tests re-indexes them.
        _make_repo(self.root, {
            "src/foo.py": "def f(): pass\n",
            "tests/test_foo.py": "def test_marker_token(): pass\n",
        })
        self._build(content="all", full=True, include_tests=True)
        self.assertIn("tests/test_foo.py", self._code_paths())
        result = self._build(content="all")  # default: tests excluded now
        self.assertNotIn("tests/test_foo.py", self._code_paths())
        log_path = self.index_dir.parent / "logs" / "index-state.log"
        self.assertTrue(log_path.is_file())
        self.assertIn("reaper code", log_path.read_text(encoding="utf-8"))
        # Layer state cleaned: re-widening re-indexes the unchanged test file.
        self._build(content="all", include_tests=True)
        self.assertIn("tests/test_foo.py", self._code_paths())

    def test_hook_spawns_all_content_reindex(self):
        # AC-2 pin: the rendered hook template and this repo's live hooks
        # spawn the indexer with --content all.
        render_src = (SCRIPTS_ROOT / "render_platform_surfaces.py").read_text(encoding="utf-8")
        self.assertIn('str(indexer), "--root", str(REPO_ROOT), "--content", "all"', render_src)
        self.assertIn('str(indexer_path), "--root", str(root), "--content", "all"', render_src)
        repo_root = SCRIPTS_ROOT.parents[2]
        hook = repo_root / ".claude" / "hooks" / "post-edit.py"
        if hook.is_file():
            self.assertIn('"--content", "all"', hook.read_text(encoding="utf-8"))

    def test_extensionless_code_names_stay_synced_with_chunker(self):
        import importlib.util as ilu
        spec = ilu.spec_from_file_location("chunker", SCRIPTS_ROOT / "chunker.py")
        ch = ilu.module_from_spec(spec)
        spec.loader.exec_module(ch)
        self.assertEqual(
            self.bi.CODE_EXTENSIONLESS_SOURCE_NAMES,
            set(ch.CODE_EXTENSIONLESS_NAMES) | set(ch.MAKEFILE_NAMES),
        )








class IndexBuildLockHeldTests(unittest.TestCase):
    """Wave 1p99o: the build lock is a fcntl record lock (POSIX) on a sentinel byte, probed
    non-destructively via F_GETLK; `ended_at` is written best-effort on clean exit."""

    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.index_dir = Path(self.tmp.name) / ".wavefoundry" / "index"
        self.index_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_held_false_when_no_lock_file(self):
        self.assertEqual(self.bi._index_build_lock_held(self.index_dir), (False, None))

    @unittest.skipIf(os.name == "nt", "cross-process F_GETLK held test is POSIX")
    def test_held_detects_concurrent_holder_and_clears_after(self):
        holder = textwrap.dedent(
            f"""
            import importlib.util, sys, time, pathlib
            spec = importlib.util.spec_from_file_location("hb", {str(INDEXER_PATH)!r})
            m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
            with m._index_build_lock(pathlib.Path(sys.argv[1])):
                print("LOCKED", flush=True); time.sleep(3)
            """
        )
        proc = subprocess.Popen([sys.executable, "-B", "-c", holder, str(self.index_dir)],
                                stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(proc.stdout.readline().strip(), "LOCKED")
            time.sleep(0.2)
            held, pid = self.bi._index_build_lock_held(self.index_dir)
            self.assertTrue(held)                      # F_GETLK sees the conflicting lock
            self.assertEqual(pid, proc.pid)            # kernel returns the holder PID
            # metadata is readable while held (lock is on the sentinel byte, not byte 0)
            meta = self.bi.read_index_build_lock_metadata(self.index_dir / self.bi.INDEX_BUILD_LOCK_NAME)
            self.assertEqual(meta.get("pid"), proc.pid)
            self.assertNotIn("ended_at", meta)         # not yet ended
        finally:
            proc.wait()
        time.sleep(0.2)
        self.assertEqual(self.bi._index_build_lock_held(self.index_dir), (False, None))

    def test_ended_at_written_on_clean_exit(self):
        with self.bi._index_build_lock(self.index_dir):
            pass
        meta = self.bi.read_index_build_lock_metadata(self.index_dir / self.bi.INDEX_BUILD_LOCK_NAME)
        self.assertIsInstance(meta.get("ended_at"), (int, float))
        # not held after a clean exit
        self.assertEqual(self.bi._index_build_lock_held(self.index_dir), (False, None))














class ReindexPendingMarkerTests(unittest.TestCase):
    """Wave 1p9am: the reindex-pending marker (turn-end coalescing sentinel)."""

    def setUp(self):
        self.bi = load_build_index()

    def test_debounce_window_raised(self):
        # Non-Stop hosts fall back to a long leading-edge debounce.
        self.assertGreaterEqual(self.bi.HOOK_REINDEX_DEBOUNCE_SECONDS, 45.0)

    def test_mark_then_consume_then_gone(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            self.assertFalse(self.bi.consume_reindex_pending(d))  # nothing pending yet
            self.assertIsNone(self.bi.reindex_pending_age(d))
            self.bi.mark_reindex_pending(d)
            self.assertIsNotNone(self.bi.reindex_pending_age(d))
            self.assertTrue(self.bi.consume_reindex_pending(d))   # consumed
            self.assertFalse(self.bi.consume_reindex_pending(d))  # already cleared
            self.assertIsNone(self.bi.reindex_pending_age(d))

    def test_consume_is_atomic_single_winner(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            self.bi.mark_reindex_pending(d)
            first = self.bi.consume_reindex_pending(d)
            second = self.bi.consume_reindex_pending(d)
            self.assertTrue(first)
            self.assertFalse(second)  # only one unlink wins

    def test_mark_creates_index_dir(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "nested" / "index"  # does not exist yet
            self.bi.mark_reindex_pending(d)
            self.assertTrue((d / self.bi.HOOK_REINDEX_PENDING_NAME).exists())

    def test_reindex_pending_age_is_recent(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            self.bi.mark_reindex_pending(d)
            age = self.bi.reindex_pending_age(d)
            self.assertIsNotNone(age)
            self.assertLess(age, 5.0)


class DocsLintHookTimeoutTests(unittest.TestCase):
    """Wave 1p9bg: the docs-lint hook timeout is generous, configurable, and fail-safe."""

    def setUp(self):
        self.bi = load_build_index()

    def _root_with_config(self, td, cfg_json):
        root = Path(td)
        (root / "docs").mkdir()
        if cfg_json is not None:
            (root / "docs" / "workflow-config.json").write_text(cfg_json, encoding="utf-8")
        return root

    def test_default_when_no_config(self):
        with tempfile.TemporaryDirectory() as td:
            root = self._root_with_config(td, None)
            self.assertEqual(
                self.bi.docs_lint_hook_timeout_seconds(root), self.bi.DOCS_LINT_HOOK_TIMEOUT_DEFAULT
            )
        self.assertGreaterEqual(self.bi.DOCS_LINT_HOOK_TIMEOUT_DEFAULT, 60.0)

    def test_override_from_config(self):
        with tempfile.TemporaryDirectory() as td:
            root = self._root_with_config(td, '{"docs_lint":{"hook_timeout_seconds":300}}')
            self.assertEqual(self.bi.docs_lint_hook_timeout_seconds(root), 300.0)

    def test_bad_values_fall_back_to_default(self):
        default = self.bi.DOCS_LINT_HOOK_TIMEOUT_DEFAULT
        for bad in ('{"docs_lint":{"hook_timeout_seconds":"lots"}}',
                    '{"docs_lint":{"hook_timeout_seconds":0}}',
                    '{"docs_lint":{"hook_timeout_seconds":-5}}',
                    '{not valid json'):
            with tempfile.TemporaryDirectory() as td:
                root = self._root_with_config(td, bad)
                self.assertEqual(self.bi.docs_lint_hook_timeout_seconds(root), default)

    def test_missing_dir_never_raises(self):
        self.assertEqual(
            self.bi.docs_lint_hook_timeout_seconds(Path("/no/such/root/xyz")),
            self.bi.DOCS_LINT_HOOK_TIMEOUT_DEFAULT,
        )


class _EpochBuildCase(unittest.TestCase):
    """Shared harness for the 1sed6 epoch/convergence fixtures."""

    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.index_dir = self.root / ".wavefoundry" / "index"
        self.iss = _store_mod()

    def tearDown(self):
        self.tmp.cleanup()

    def _run_build(self, full: bool = False, content: str = "all") -> dict:
        docs_mock = _make_embedder_mock(dim=4)
        code_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", side_effect=[docs_mock, code_mock]):
            return self.bi.build_index(self.root, full=full, content=content, verbose=False)

    def _generation(self) -> int:
        state = self.iss.read_build_state(self.index_dir)
        return state["generation"] if state else -1


class ProjectLayerFreshnessTests(_EpochBuildCase):
    """1seav / 1sbxq AC-2: the cheap per-layer freshness signal — layer-
    crossing regressions in BOTH directions, added/deleted paths, empty
    layers, chunker mismatch, and the honesty rule (unknown, never silently
    current)."""

    def _freshness(self):
        return self.bi.project_layer_freshness(self.root)

    def _seed(self):
        _make_repo(self.root, {
            "src/foo.py": "def f(): return 1\n",
            "docs/guide.md": "## Intro\n\nHello.\n",
        })
        self._run_build(full=True)

    def test_current_after_full_build(self):
        self._seed()
        v = self._freshness()
        self.assertIs(v["stale"], False)
        self.assertEqual(v["reason"], "current")

    def test_ignore_listed_recorded_state_path_stays_current(self):
        """1sq9h regression: an ignore-listed path (the generated
        codebase map) is stamped into docs layer state by the build but is
        filtered out of the freshness walk and snapshot. It must NOT be read
        as 'recorded path gone'. Pre-fix this returned stale=True / reason
        'layer behind broad snapshot' on every repo with a codebase map, and
        no build could clear it."""
        _make_repo(self.root, {
            "src/foo.py": "def f(): return 1\n",
            "docs/guide.md": "## Intro\n\nHello.\n",
            "docs/references/codebase-map.md": "# Codebase Map\n\nGenerated artifact.\n",
        })
        self._run_build(full=True)
        # Non-vacuity precondition: the ignore-listed path really is recorded in
        # layer state (otherwise the false-stale branch is never exercised).
        state = self.iss.layer_hashes(self.index_dir, "docs") or {}
        self.assertIn(
            "docs/references/codebase-map.md", state,
            "precondition: build must stamp the ignore-listed path into docs layer state",
        )
        self.assertIn("docs/references/codebase-map.md", self.bi._PROJECT_STALE_IGNORE_PATHS)
        v = self._freshness()
        self.assertIs(v["stale"], False, v.get("reason"))
        self.assertEqual(v["reason"], "current")

    def test_simple_edit_reads_stale(self):
        self._seed()
        (self.root / "src" / "foo.py").write_text("def f(): return 2\n", encoding="utf-8")
        self.assertIs(self._freshness()["stale"], True)

    def test_layer_crossing_code_edit_survives_docs_only_build(self):
        """The 1sek8 poison direction: edit a code file, run a docs-only
        build that also processes a docs change (the broad snapshot stamps
        the code file's fresh hash) — freshness must STILL read stale until
        a code/all build embeds it."""
        self._seed()
        (self.root / "src" / "foo.py").write_text("def f(): return 2\n", encoding="utf-8")
        (self.root / "docs" / "guide.md").write_text("## Intro\n\nChanged.\n", encoding="utf-8")
        docs_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", side_effect=[docs_mock]):
            self.bi.build_index(self.root, full=False, content="docs", verbose=False)
        v = self._freshness()
        self.assertIs(v["stale"], True, "broad snapshot stamped the code hash; the code layer is behind")
        self.assertIs(v["layers"]["code"], True)
        # A second docs-only build cannot clear it...
        docs_mock2 = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", side_effect=[docs_mock2]):
            self.bi.build_index(self.root, full=False, content="docs", verbose=False)
        self.assertIs(self._freshness()["stale"], True)
        # ...a code/all build does.
        with patch.object(self.bi, "_get_embedder",
                          side_effect=[_make_embedder_mock(dim=4), _make_embedder_mock(dim=4)]):
            self.bi.build_index(self.root, full=False, content="all", verbose=False)
        self.assertIs(self._freshness()["stale"], False)

    def test_layer_crossing_inverse_docs_edit_survives_code_only_build(self):
        """The inverse direction (code_ask searches BOTH layers): edit a
        docs file, run a code-only build that also processes a code change —
        stale until a docs/all build."""
        self._seed()
        (self.root / "docs" / "guide.md").write_text("## Intro\n\nChanged.\n", encoding="utf-8")
        (self.root / "src" / "foo.py").write_text("def f(): return 3\n", encoding="utf-8")
        with patch.object(self.bi, "_get_embedder", side_effect=[_make_embedder_mock(dim=4)]):
            self.bi.build_index(self.root, full=False, content="code", verbose=False)
        v = self._freshness()
        self.assertIs(v["stale"], True)
        self.assertIs(v["layers"]["docs"], True)
        with patch.object(self.bi, "_get_embedder",
                          side_effect=[_make_embedder_mock(dim=4), _make_embedder_mock(dim=4)]):
            self.bi.build_index(self.root, full=False, content="all", verbose=False)
        self.assertIs(self._freshness()["stale"], False)

    def test_added_and_deleted_paths_read_stale(self):
        self._seed()
        (self.root / "src" / "bar.py").write_text("def g(): pass\n", encoding="utf-8")
        self.assertIs(self._freshness()["stale"], True, "added path")
        with patch.object(self.bi, "_get_embedder",
                          side_effect=[_make_embedder_mock(dim=4), _make_embedder_mock(dim=4)]):
            self.bi.build_index(self.root, full=False, content="all", verbose=False)
        self.assertIs(self._freshness()["stale"], False)
        (self.root / "src" / "bar.py").unlink()
        self.assertIs(self._freshness()["stale"], True, "deleted path")

    def test_unreadable_modified_file_reads_unknown_not_current(self):
        """Review fix (honesty): a stat-mismatched file whose hash read fails
        (permissions/AV lock) makes the walk pass undeterminable — the
        verdict must be unknown, never current, even though the layer hashes
        alone still match."""
        import os, stat
        self._seed()
        target = self.root / "src" / "foo.py"
        target.write_text("def f(): return 99\n", encoding="utf-8")
        os.chmod(target, 0)
        try:
            v = self._freshness()
        finally:
            os.chmod(target, stat.S_IRUSR | stat.S_IWUSR)
        self.assertIsNone(v["stale"],
                          "an undeterminable walk must not read current")
        self.assertIn("undeterminable", v["reason"])
        # Once readable again, the truth surfaces.
        self.assertIs(self._freshness()["stale"], True)

    def test_legitimately_empty_layer_reads_current(self):
        """A repo with no docs corpus: the empty docs layer is current, not
        stale/unknown."""
        _make_repo(self.root, {"src/foo.py": "def f(): return 1\n"})
        self._run_build(full=True)
        v = self._freshness()
        self.assertIs(v["stale"], False)

    def test_chunker_mismatch_reads_stale(self):
        self._seed()
        store = self.bi._get_index_state_store()
        snapshot = store.read_build_summary(self.index_dir)
        stale_meta = dict(snapshot)
        stale_meta["chunker_versions"] = {"docs": "0", "code": "0"}
        stale_meta["file_meta"] = self.bi._load_meta(self.index_dir).get("file_meta", {})
        store.write_build_bookkeeping(self.index_dir, stale_meta)
        v = self._freshness()
        self.assertIs(v["stale"], True)
        self.assertIs(v["chunker_stale"], True)

    def test_no_store_reads_unknown_never_current(self):
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        v = self._freshness()
        self.assertIsNone(v["stale"], "no snapshot = unknown, never current")

    def test_helper_exception_reads_unknown(self):
        self._seed()
        # The walk seam raising → undeterminable walk → unknown.
        with patch.object(self.bi, "_detect_changes", side_effect=RuntimeError("boom")):
            v = self._freshness()
        self.assertIsNone(v["stale"])
        self.assertIn("undeterminable", v["reason"])
        # A failure OUTSIDE the walk (e.g. the store read) → unknown too.
        with patch.object(self.bi, "walk_repo", side_effect=RuntimeError("boom")):
            v2 = self._freshness()
        self.assertIsNone(v2["stale"])
        self.assertIn("error", v2["reason"])

    def test_added_code_file_survives_docs_only_build(self):
        """Review reproduction (P1): full build → ADD a code file → docs-only
        build (stamps the new file into the broad snapshot) → must read
        stale until a code/all build processes it."""
        self._seed()
        (self.root / "src" / "bar.py").write_text("def g(): pass\n", encoding="utf-8")
        (self.root / "docs" / "guide.md").write_text("## Intro\n\nChanged.\n", encoding="utf-8")
        with patch.object(self.bi, "_get_embedder", side_effect=[_make_embedder_mock(dim=4)]):
            self.bi.build_index(self.root, full=False, content="docs", verbose=False)
        v = self._freshness()
        self.assertIs(v["stale"], True,
                      "an added code file stamped by a docs-only build must read stale")
        self.assertIs(v["layers"]["code"], True)
        with patch.object(self.bi, "_get_embedder",
                          side_effect=[_make_embedder_mock(dim=4), _make_embedder_mock(dim=4)]):
            self.bi.build_index(self.root, full=False, content="all", verbose=False)
        self.assertIs(self._freshness()["stale"], False)

    def test_unreadable_required_layer_state_reads_unknown(self):
        """Review fix: layer_hashes returning None for a layer with a
        non-empty eligible set → unknown, never current."""
        self._seed()
        store = self.bi._get_index_state_store()
        with patch.object(store, "layer_hashes", return_value=None):
            v = self._freshness()
        self.assertIsNone(v["stale"])
        self.assertIn("unreadable", v["reason"])


class LegacyConvergenceTests(_EpochBuildCase):
    """AC-6: a legacy installation (Lance + meta.json, no state store)
    converges by reconstruction — legacy JSON is never authoritative input
    and is removed only after a successful completed epoch."""

    def test_legacy_json_is_never_authority_and_removed_after_convergence(self):
        _make_repo(self.root, {
            "src/foo.py": "def f(): return 1\n",
            "docs/guide.md": "## Intro\n\nHello.\n",
        })
        first = self._run_build(full=True)
        self.assertFalse(first.get("failed"))
        # Fabricate the legacy layout: the store's snapshot exported to
        # meta.json (so the JSON claims every file is current), store gone.
        snapshot = _read_meta_store(self.index_dir)
        self.assertTrue(snapshot.get("file_meta"))
        (self.index_dir / "meta.json").write_text(json.dumps(snapshot), encoding="utf-8")
        for suffix in ("", "-wal", "-shm"):
            p = Path(str(index_paths.runtime_database_path(self.index_dir)) + suffix)
            if p.exists():
                p.unlink()
        # An ordinary incremental build must treat the empty store — not the
        # JSON — as the state authority: everything re-indexes.
        result = self._run_build(full=False)
        self.assertFalse(result.get("failed"))
        self.assertGreater(result["files_indexed"], 0,
                           "legacy meta.json must not satisfy freshness")
        # Converged: completed epoch, repopulated state, legacy JSON removed.
        self.assertIsNotNone(self.iss.build_epoch_token(self.index_dir))
        self.assertTrue(_read_meta_store(self.index_dir).get("file_meta"))
        self.assertFalse((self.index_dir / "meta.json").exists())

    def test_legacy_json_survives_a_failed_convergence(self):
        """Removal happens ONLY after success: a build that fails before
        finalization leaves the legacy file (and no complete epoch) behind."""
        _make_repo(self.root, {"src/foo.py": "def f(): return 1\n"})
        self._run_build(full=True)
        (self.index_dir / "meta.json").write_text("{}", encoding="utf-8")
        store = self.bi._get_index_state_store()
        (self.root / "src" / "foo.py").write_text("def f(): return 2\n", encoding="utf-8")
        with patch.object(store, "write_build_bookkeeping_locked", side_effect=RuntimeError("disk full")):
            result = self._run_build(full=False)
        self.assertTrue(result.get("failed"))
        self.assertTrue((self.index_dir / "meta.json").exists(),
                        "legacy JSON must not be removed before convergence")
        self.assertIsNone(self.iss.build_epoch_token(self.index_dir))


class DryRunIdleMaintenanceTests(_EpochBuildCase):
    """1x81w: the public unlocked preview never executes idle maintenance."""

    def _seed(self):
        _make_repo(self.root, {
            "src/app.py": "def app():\n    return 1\n",
            **{f"docs/note_{i}.md": f"## Note {i}\n\nBody {i}.\n" for i in range(10)},
        })
        self._run_build(full=True)

    def _sql(self, statement, params=()):
        import sqlite3
        conn = sqlite3.connect(str(index_paths.runtime_database_path(self.index_dir)))
        try:
            with conn:
                conn.execute(statement, params)
        finally:
            conn.close()

    def _snapshot(self):
        import hashlib
        import sqlite3
        snapshot = {}
        for p in self.index_dir.rglob("*"):
            if not p.is_file() or p.name.endswith(("-wal", "-shm")):
                continue
            key = str(p.relative_to(self.index_dir))
            if p.suffix == ".sqlite":
                # SQLite read locks can change SHM bytes even in mode=ro.
                # Compare every persisted row (including meta/epoch) instead;
                # Lance and all other index artifacts remain byte comparisons.
                conn = sqlite3.connect(p.as_uri() + "?mode=ro", uri=True)
                try:
                    snapshot[key] = tuple(conn.iterdump())
                finally:
                    conn.close()
            else:
                snapshot[key] = hashlib.sha256(p.read_bytes()).hexdigest()
        return snapshot

    def _preview(self, pending=None, content="all"):
        before = self._snapshot()
        epoch = self.iss.read_build_state(self.index_dir)
        err = io.StringIO()
        with patch.object(self.bi, "_index_build_lock", side_effect=AssertionError("preview took lock")), \
                redirect_stderr(err):
            result = self.bi.build_index(self.root, content=content, dry_run=True)
        self.assertEqual(self._snapshot(), before, "dry-run changed an index file")
        self.assertEqual(self.iss.read_build_state(self.index_dir), epoch)
        self.assertTrue(result.get("dry_run"), result)
        self.assertEqual(result.get("up_to_date"), pending is None, result)
        if pending:
            self.assertTrue(result["pending_maintenance"][pending], result)
            self.assertIn(pending, err.getvalue())
        else:
            self.assertFalse(any(result["pending_maintenance"].values()), result)
        return result

    def test_dirty_epoch_dry_run_is_byte_identical_and_reports_recovery(self):
        self._seed()
        self.iss.begin_build_epoch(self.index_dir, "interrupted")
        self._preview("dirty_epoch")

    def test_drift_clear_dry_run_preserves_meta_and_reports_pending(self):
        self._seed()
        self._sql("INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)",
                  (self.iss.META_DRIFT_FINGERPRINT, "stale-git-fingerprint"))
        self.assertTrue(self.iss.has_drift_state(self.index_dir))
        self._preview("drift_clear")
        self._run_build()
        self.assertFalse(self.iss.has_drift_state(self.index_dir))

    def test_heal_dry_run_preserves_cold_store_and_reports_pending(self):
        self._seed()
        self._sql("INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)",
                  (self.iss.META_CHUNK_INDEX_COLD, "1"))
        self.assertTrue(self.bi._chunk_index_needs_heal(self.index_dir))
        self._preview("chunk_heal")
        self._run_build()
        self.assertFalse(self.bi._chunk_index_needs_heal(self.index_dir))

    def test_orphan_dry_run_preserves_sidecar_row_and_reports_count(self):
        self._seed()
        self._sql("INSERT INTO secret_scan_cache "
                  "(path,content_hash,rules_fingerprint,scanned_at,clean,finding_refs) "
                  "VALUES ('docs/phantom.md','x','y',0,1,'[]')")
        result = self._preview("orphan_reconcile")
        self.assertEqual(result["orphan_paths_pending"]["secret_scan_cache"], 1)
        result = self._run_build()
        self.assertEqual(result["orphan_rows_reconciled"]["secret_scan_cache"], 1)

    def test_reap_dry_run_preserves_lance_and_reports_path_count(self):
        self._seed()
        meta = _read_meta_store(self.index_dir)
        meta["file_meta"].pop("docs/note_0.md")
        (self.root / "docs/note_0.md").unlink()
        _seed_meta_store(self.index_dir, meta)
        result = self._preview("stranded_reap")
        self.assertEqual(result["stranded_paths_pending"]["docs"], 1)
        result = self._run_build()
        self.assertGreater(result["stranded_rows_reaped"], 0)

    def test_missing_lance_dirty_preview_preserves_layer_hashes(self):
        import shutil
        self._seed()
        self.iss.begin_build_epoch(self.index_dir, "interrupted")
        conn=self.iss.open_read_only(self.index_dir)
        conn.close()
        store=self.iss.IndexStateStore(self.index_dir)
        store._conn.execute("DELETE FROM vectors_code")
        store.close()
        before = self.iss.layer_hashes(self.index_dir, "code")
        self.assertTrue(before)
        self._preview("dirty_epoch", content="graph")
        self.assertEqual(self.iss.layer_hashes(self.index_dir, "code"), before)

    def test_healthy_noop_dry_run_stays_byte_identical(self):
        self._seed()
        self._preview()

    def test_cli_dry_run_reports_dirty_epoch_without_writing(self):
        self._seed()
        self.iss.begin_build_epoch(self.index_dir, "interrupted")
        before = self._snapshot()
        err = io.StringIO()
        with redirect_stderr(err), \
                patch.object(self.bi, "_enable_timestamped_stdio"), \
                patch.object(self.bi, "_index_build_lock", side_effect=AssertionError("preview took lock")):
            exit_code = self.bi.main(["--root", str(self.root), "--content", "all", "--dry-run"])
        self.assertEqual(exit_code, 0)
        self.assertEqual(self._snapshot(), before)
        self.assertIn("dirty_epoch", err.getvalue())


class IdleDocLinkRecoveryTests(_EpochBuildCase):
    """1x8e1/1x81w: exercise the real walk, idle caller, lock and graph store."""

    _snapshot = DryRunIdleMaintenanceTests._snapshot

    def _payload(self):
        return _published_graph_payload(self.bi, self.root)

    def _assert_link(self, target, present):
        payload = self._payload()
        edges = {(e["source"], e["target"], e["relation"]) for e in payload["edges"]}
        self.assertEqual(("docs/linker.md", target, "doc_references_doc") in edges, present)
        self.assertEqual("docs/linker.md" in {n["id"] for n in payload["nodes"]}, present)
        return payload

    def _defer_link(self, target, *, orphan=False):
        _make_repo(self.root, {
            "src/app.py": "def app():\n    return 1\n",
            "docs/linker.md": f"See [later](/{target}).\n",
            **({"src/retired.py": "def retired(): return 0\n"} if orphan else {}),
        })
        self._run_build(full=True)
        self._assert_link(target, False)
        dest = self.root / target
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("def later():\n    return 2\n" if target.endswith(".py") else "cache/\n")
        real_read = Path.read_text
        denied_reads = []

        def denied(path, *args, **kwargs):
            if path == self.root / "docs/linker.md":
                denied_reads.append(path)
                raise PermissionError(13, "injected referring-doc read failure", str(path))
            return real_read(path, *args, **kwargs)

        with patch.object(Path, "read_text", new=denied):
            self._run_build()
        self.assertTrue(denied_reads, "precondition: target creation reached the referring-doc rescan")
        self._assert_link(target, False)

    def _exercise_recovery(self, target, *, dirty=False, orphan=False):
        import contextlib
        self._defer_link(target, orphan=orphan)
        if orphan:
            meta = _read_meta_store(self.index_dir)
            meta["file_meta"].pop("src/retired.py")
            (self.root / "src/retired.py").unlink()
            _seed_meta_store(self.index_dir, meta)
        if dirty:
            self.iss.begin_build_epoch(self.index_dir, "interrupted-with-pending-link")
        before = self._snapshot()
        epoch = self.iss.read_build_state(self.index_dir)
        with patch.object(self.bi, "_build_graph_artifacts", side_effect=AssertionError("dry-run graph mutation")), \
                patch.object(self.bi, "_index_build_lock", side_effect=AssertionError("dry-run took lock")), \
                redirect_stderr(io.StringIO()):
            preview = self.bi.build_index(self.root, content="all", dry_run=True)
        self.assertTrue(preview["dry_run"])
        self.assertFalse(preview["up_to_date"])
        self.assertTrue(preview["pending_maintenance"]["graph_recovery"])
        self.assertEqual(preview["pending_maintenance"]["dirty_epoch"], dirty)
        if orphan:
            self.assertTrue(preview["pending_maintenance"]["orphan_reconcile"])
            self.assertEqual(preview["orphan_paths_pending"]["graph"], 1)

        self.assertEqual(self._snapshot(), before)
        self.assertEqual(self.iss.read_build_state(self.index_dir), epoch)

        real_lock = self.bi._index_build_lock
        real_graph = self.bi._build_graph_artifacts
        lock_held = []

        @contextlib.contextmanager
        def checked_lock(*args, **kwargs):
            with real_lock(*args, **kwargs):
                lock_held.append(True)
                try:
                    yield
                finally:
                    lock_held.pop()

        def checked_graph(**kwargs):
            self.assertTrue(lock_held, "graph recovery must run under the public build lock")
            self.assertEqual(self.iss.read_build_state(self.index_dir)["status"], "building")
            self.assertIsNotNone(kwargs.get("doc_link_repair_plan"))
            return real_graph(**kwargs)

        with patch.object(self.bi, "_index_build_lock", new=checked_lock), \
                patch.object(self.bi, "_build_graph_artifacts", side_effect=checked_graph) as graph, \
                patch.object(self.bi._get_graph_indexer(), "retire_orphaned_graph_paths",
                             side_effect=AssertionError("second graph merge after repair")) as retire, \
                patch.object(self.bi, "_enable_timestamped_stdio"), \
                redirect_stderr(io.StringIO()):
            # Actual CLI entry, with the file changes already acknowledged by
            # the previous build: only the retained per-doc obligation remains.
            rc = self.bi.main(["--root", str(self.root), "--content", "all"])
        self.assertEqual(rc, 0)
        self.assertEqual(graph.call_count, 1)
        self.assertEqual(retire.call_count, 0)

        payload = self._assert_link(target, True)
        if orphan:
            self.assertNotIn("src/retired.py", {n["id"] for n in payload["nodes"]})
            self.assertNotIn("src/retired.py", {
                row["path"] for row in _read_index_chunks(self.index_dir, "code")
            })
        if target.endswith(".gitignore"):
            self.assertNotIn(target, {n["id"] for n in payload["nodes"]})
        self.assertGreater(self._generation(), epoch["generation"])
        self.assertEqual(self.iss.read_build_state(self.index_dir)["status"], "complete")
        generation = self._generation()
        with patch.object(self.bi, "_build_graph_artifacts", side_effect=AssertionError("resolved link re-dispatched")):
            result = self._run_build()
        self.assertTrue(result["up_to_date"])
        self.assertEqual(self._generation(), generation)
        self._assert_link(target, True)

    def test_unchanged_public_recovery_after_failed_doc_read(self):
        self._exercise_recovery("src/later.py")

    def test_nodeless_link_and_dirty_epoch_share_one_locked_recovery(self):
        self._exercise_recovery("assets/.gitignore", dirty=True)


    def test_pending_link_and_orphan_reap_share_one_graph_merge(self):
        self._exercise_recovery("src/later.py", orphan=True)

    def _assert_publication_recovery(self, target):
        gi = self.bi._get_graph_indexer()
        before, epoch = self._snapshot(), self.iss.read_build_state(self.index_dir)
        with patch.object(self.bi, "_build_graph_artifacts", side_effect=AssertionError("preview mutated graph")), \
                patch.object(self.bi, "_index_build_lock", side_effect=AssertionError("preview took lock")), \
                redirect_stderr(io.StringIO()):
            preview = self.bi.build_index(self.root, content="all", dry_run=True)
        self.assertTrue(preview["pending_maintenance"]["graph_recovery"])
        self.assertFalse(preview["up_to_date"])
        self.assertEqual(self._snapshot(), before)
        self.assertEqual(self.iss.read_build_state(self.index_dir), epoch)
        with patch.object(self.bi, "_build_graph_artifacts", wraps=self.bi._build_graph_artifacts) as graph:
            recovered = self._run_build()
        self.assertTrue(recovered["graph_recovery_attempted"])
        self.assertEqual(graph.call_count, 1)
        payload = self._assert_link(target, True)
        self.assertIn(("docs/linker.md", target, "doc_references_doc", "EXTRACTED"), {
            (e["source"], e["target"], e["relation"], e.get("confidence")) for e in payload["edges"]
        })
        self.assertEqual(self._graph_meta()["graph_rows_state"], "published")
        self.assertEqual(self.iss.read_build_state(self.index_dir)["status"], "complete")
        generation = self._generation()
        with patch.object(self.bi, "_build_graph_artifacts", side_effect=AssertionError("repaired binding re-dispatched")):
            self.assertTrue(self._run_build()["up_to_date"])
        self.assertEqual(self._generation(), generation)

    def _graph_meta(self) -> dict:
        gi = self.bi._get_graph_indexer()
        conn = self.iss.open_read_only(self.index_dir)
        try:
            cut = len(gi.GRAPH_META_PREFIX)
            return {
                str(k)[cut:]: str(v)
                for k, v in conn.execute(
                    "SELECT key, value FROM meta WHERE key LIKE ?",
                    (gi.GRAPH_META_PREFIX + "%",),
                )
            }
        finally:
            conn.close()

    def _merge_state(self) -> dict:
        gi = self.bi._get_graph_indexer()
        conn = self.iss.open_read_only(self.index_dir)
        try:
            return gi._read_merge_state_rows(conn, self._graph_meta()) or {}
        finally:
            conn.close()

    def test_a_missing_retired_graph_folder_is_not_a_graph_fault(self):
        """Wave 1xny6 lane L6b retired the derived payload FILE entirely, so
        there is no artifact whose absence, size or mtime could request a
        rebuild. Its folder must not even exist after an ordinary build. What
        remains a real graph fault is merge state that is GONE, and it still
        routes to the real locked recovery."""
        target = "src/later.py"
        self._defer_link(target)
        self._run_build()
        self._exercise_recovery_seeded = True
        self.assertFalse((self.index_dir / "graph").exists(),
                         "an ordinary build recreated the retired graph folder")
        with patch.object(self.bi, "_build_graph_artifacts",
                          side_effect=AssertionError("preview mutated graph")), \
                patch.object(self.bi, "_index_build_lock",
                             side_effect=AssertionError("preview took lock")), \
                redirect_stderr(io.StringIO()):
            preview = self.bi.build_index(self.root, content="all", dry_run=True)
        self.assertFalse(
            preview["pending_maintenance"]["graph_recovery"],
            "an absent derived artifact must not request a graph rebuild",
        )
        store = self.iss.IndexStateStore(self.index_dir)
        try:
            with store._conn:
                store._conn.execute("DELETE FROM graph_merge_state")
        finally:
            store.close()
        self._assert_publication_recovery(target)


class UnifiedPublicationParticipantTests(_EpochBuildCase):
    """Wave 1xny6 (1xny5-ref): one publication transaction, explicit participants.

    Everything asserted here is observed through a REAL build: the graph rows,
    the extraction manifest, the community rows, the per-layer bookkeeping and
    the final generation either all appear together or none of them do.
    """

    def _conn(self):
        return self.iss.open_read_only(self.index_dir)

    def _census(self) -> dict:
        conn = self._conn()
        if conn is None:
            return {}
        try:
            import graph_store

            tables = (
                "chunks_docs", "chunks_code", "graph_nodes", "graph_edges",
                "graph_file_state", "graph_merge_state", "graph_communities",
                "graph_community_members", "graph_analysis", "build_layer_state",
            )
            out = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
            assert set(graph_store.GRAPH_TABLES) <= set(tables) | {"graph_symbol_chunks"}
            return out
        finally:
            conn.close()

    def _graph_meta(self) -> dict:
        gi = self.bi._get_graph_indexer()
        conn = self._conn()
        try:
            cut = len(gi.GRAPH_META_PREFIX)
            return {str(k)[cut:]: str(v) for k, v in conn.execute(
                "SELECT key, value FROM meta WHERE key LIKE ?",
                (gi.GRAPH_META_PREFIX + "%",))}
        finally:
            conn.close()

    def _seed(self):
        # Same directory so the import resolves to a PROJECT node: the
        # cross-file `calls` edge is the relationship these tests are about.
        _make_repo(self.root, {
            "pkg_a/lib.py": "def helper(value):\n    return value + 1\n",
            "pkg_a/caller.py": "def dispatch():\n    return helper(2)\n",
            "docs/guide.md": "# Guide\n\nSee `pkg_a/lib.py` and `helper`.\n",
        })

    def test_all_content_publication_commits_every_participant_together(self):
        self._seed()
        self.assertEqual(self._census(), {})
        result = self._run_build(full=True)
        self.assertNotIn("failed", result)

        census = self._census()
        for table, count in census.items():
            self.assertGreater(count, 0, f"{table} must be published by an all-content build")
        # FTS is derived from the canonical chunks committed above.
        conn = self._conn()
        try:
            fts = conn.execute("SELECT COUNT(*) FROM fts_code").fetchone()[0]
            vectors = conn.execute("SELECT COUNT(*) FROM vectors_code").fetchone()[0]
        finally:
            conn.close()
        self.assertGreater(fts, 0)
        self.assertGreater(vectors, 0)

        state = self.iss.read_build_state(self.index_dir)
        self.assertEqual(state["status"], "complete")
        layers = self.iss.read_build_layer_state(self.index_dir)
        self.assertEqual(sorted(layers), ["code", "docs", "graph"])
        for layer, row in layers.items():
            self.assertEqual(row["status"], "published", layer)
            self.assertEqual(row["generation"], state["generation"], layer)
            self.assertEqual(row["attempt_id"], state["attempt_id"], layer)
        self.assertEqual(self._graph_meta()["graph_rows_state"], "published")

        # Wave 1xny6 lane L6b: the derived artifact is retired. The PUBLISHED
        # payload is the one rebuilt from the rows and their header, and it
        # must carry neither the prepared SQL (not serialisable at all) nor the
        # per-build instrumentation. No file, and no retired folder either.
        gi = self.bi._get_graph_indexer()
        published = gi.read_published_graph_snapshot(self.root, "project")
        self.assertIsInstance(published, dict)
        self.assertNotIn("_publication", published["payload"])
        self.assertNotIn("merge_stats", published["payload"])
        self.assertEqual({n["id"] for n in published["payload"]["nodes"]}, self._node_ids())
        self.assertFalse((self.index_dir / "graph").exists())

    def test_small_full_incremental_noop_and_graph_builds_create_no_preparation_files(self):
        import sqlite_vector_store as vectors
        import sqlite_runtime

        self._seed()
        real_directory = vectors.tempfile.TemporaryDirectory
        real_connect = sqlite_runtime.connect
        preparation_attempts = []

        def directory(*args, **kwargs):
            if kwargs.get("prefix", "").startswith("wavefoundry-sqlite-prepared-"):
                preparation_attempts.append("directory")
                raise AssertionError("small build attempted a disk preparation directory")
            return real_directory(*args, **kwargs)

        def connect(path, *args, **kwargs):
            if Path(path).name == "prepared.sqlite":
                preparation_attempts.append("database")
                raise AssertionError("small build attempted a preparation database")
            return real_connect(path, *args, **kwargs)

        with patch.object(vectors.tempfile, "TemporaryDirectory", directory), patch.object(
                sqlite_runtime, "connect", connect):
            full = self._run_build(full=True)
            self.assertNotIn("failed", full)
            self.assertGreater(self._census()["chunks_code"], 0)
            idle = self._run_build()
            self.assertTrue(idle["up_to_date"])
            target = self.root / "pkg_a" / "lib.py"
            target.write_text("def helper(value):\n    return value + 2\n")
            graph = self._run_build(content="graph")
            self.assertNotIn("failed", graph)
            delta = self._run_build()
            self.assertNotIn("failed", delta)
            self.assertGreater(self._census()["graph_nodes"], 0)
        self.assertEqual(preparation_attempts, [])

    def test_publication_timer_excludes_acquisition_and_includes_commit(self):
        import sqlite_runtime
        from types import SimpleNamespace

        self._seed()
        clock = [0.0]
        real_connect = sqlite_runtime.connect
        boundaries = []

        class TimedConnection:
            def __init__(self, conn):
                self.conn = conn

            def __enter__(self):
                self.conn.__enter__()
                return self

            def __exit__(self, *args):
                return self.conn.__exit__(*args)

            def execute(self, sql, *args, **kwargs):
                head = sql.strip().upper()
                if head == "COMMIT":
                    clock[0] += 0.1
                result = self.conn.execute(sql, *args, **kwargs)
                if head == "BEGIN IMMEDIATE":
                    # Deterministic elapsed acquisition time, ending at the
                    # actual native BEGIN return. SQL remains fully real.
                    clock[0] += 0.3
                if head in ("BEGIN IMMEDIATE", "COMMIT"):
                    boundaries.append(head)
                return result

            def __getattr__(self, name):
                return getattr(self.conn, name)

        with patch.object(sqlite_runtime, "connect", side_effect=lambda *a, **kw:
                          TimedConnection(real_connect(*a, **kw))), patch.object(
                              self.bi, "time", SimpleNamespace(**{
                                  **vars(self.bi.time), "monotonic": lambda: clock[0]})):
            result = self._run_build(full=True)
        self.assertNotIn("failed", result)
        self.assertIn("BEGIN IMMEDIATE", boundaries)
        self.assertIn("COMMIT", boundaries)
        self.assertAlmostEqual(result["publication_held_ms"], 100.0, places=2)
        self.assertGreater(self._census()["graph_nodes"], 0)

    def test_source_read_failure_preserves_published_graph_and_retry_recovers(self):
        self._seed()
        self.assertNotIn("failed", self._run_build(full=True))
        before, generation = self._census(), self._generation()
        target = self.root / "pkg_a" / "lib.py"
        target.write_text("def helper(value):\n    return value + 2\n\ndef extra():\n    return 0\n")
        gi = self.bi._get_graph_indexer()
        real_read = Path.read_text
        for threshold in (1, 100000):
            with self.subTest(read_threads=threshold == 1):
                seen = []
                def denied(path, *args, **kwargs):
                    if path == target:
                        seen.append(path)
                        raise PermissionError("injected graph source denial")
                    return real_read(path, *args, **kwargs)
                with patch.object(Path, "read_text", denied), patch.object(
                        gi, "_PARALLEL_EXTRACTION_THRESHOLD", threshold):
                    with self.assertRaisesRegex(OSError, "graph extraction could not read pkg_a/lib.py"):
                        self._run_build(full=True, content="graph")
                self.assertTrue(seen, "the eligible source must reach the actual read")
                self.assertEqual(self._census(), before)
                self.assertEqual(self._generation(), generation)
        self.assertNotIn("failed", self._run_build(full=True, content="graph"))
        self.assertIn("pkg_a/lib.py::extra", self._node_ids())

    def test_injected_rollback_publishes_nothing_and_leaves_a_recoverable_state(self):
        self._seed()
        self._run_build(full=True)
        before, gen = self._census(), self._generation()
        (self.root / "pkg_a" / "lib.py").write_text(
            "def helper(value):\n    return value + 2\n\n\ndef extra():\n    return 0\n")

        gi = self.bi._get_graph_indexer()
        original = gi.GraphPublication.apply

        def _boom(pub_self, conn):
            original(pub_self, conn)
            raise RuntimeError("injected participant fault")

        with patch.object(gi.GraphPublication, "apply", _boom):
            result = self._run_build()
        self.assertTrue(result.get("failed"))
        self.assertEqual(self._census(), before, "a failed attempt must publish nothing")
        self.assertEqual(self._generation(), gen, "the generation never advanced")

        recovered = self._run_build()
        self.assertNotIn("failed", recovered)
        self.assertGreater(self._generation(), gen)
        self.assertIn("pkg_a/lib.py::extra", self._node_ids())

    def test_process_interruption_before_commit_leaves_the_old_state(self):
        """A hard interruption (BaseException, as a signal delivers) inside the
        transaction is the same one window: rollback, old state, recoverable."""
        self._seed()
        self._run_build(full=True)
        before, gen = self._census(), self._generation()
        (self.root / "pkg_a" / "lib.py").write_text("def helper(v):\n    return v + 9\n")

        gi = self.bi._get_graph_indexer()

        def _interrupt(pub_self, conn):
            raise KeyboardInterrupt("injected process interruption")

        with patch.object(gi.GraphPublication, "apply", _interrupt):
            with self.assertRaises(KeyboardInterrupt):
                self._run_build()
        self.assertEqual(self._census(), before)
        self.assertEqual(self._generation(), gen)
        self.assertNotIn("failed", self._run_build())

    def test_stale_attempt_cannot_publish(self):
        self._seed()
        self._run_build(full=True)
        before, gen = self._census(), self._generation()
        (self.root / "pkg_a" / "lib.py").write_text("def helper(v):\n    return v + 3\n")

        # A newer attempt opens the epoch while this one holds prepared rows.
        # Recorded BEFORE the publication transaction opens, so the fence at
        # the top of that transaction is what refuses -- not the finalize CAS
        # after a commit that already landed.
        superseded = self._supersede_after_graph_preparation("rival-build")
        with superseded["patch"]:
            result = self._run_build()
        self.assertEqual(superseded["fired"], 1, "precondition: the rival attempt was recorded")
        self.assertTrue(result.get("failed"))
        self.assertIn("no longer current", result.get("failure", ""), result)
        self.assertEqual(self._census(), before, "a superseded attempt must publish nothing")
        self.assertEqual(self._generation(), gen)

    def _supersede_after_graph_preparation(self, attempt_id: str):
        """Record a rival attempt id between graph PREPARATION and publication.

        Both publication paths prepare the graph rows before opening their
        transaction, so this lands the rival in the exact window the
        in-transaction fence exists to cover.
        """
        state = {"fired": 0}
        real = self.bi._build_graph_artifacts

        def _wrapped(*args, **kwargs):
            out = real(*args, **kwargs)
            if state["fired"] == 0:
                state["fired"] += 1
                other = self.iss._full_durable_connection(self.index_dir)
                try:
                    with other:
                        other.execute(
                            "UPDATE build_state SET attempt_id=?, status='building' "
                            "WHERE id=1", (attempt_id,))
                finally:
                    other.close()
            return out

        state["patch"] = patch.object(self.bi, "_build_graph_artifacts", _wrapped)
        return state

    def _node_ids(self) -> set:
        conn = self._conn()
        try:
            return {str(r[0]) for r in conn.execute("SELECT node_id FROM graph_nodes")}
        finally:
            conn.close()

    def _edges(self) -> set:
        conn = self._conn()
        try:
            return {(str(r[0]), str(r[1]), str(r[2])) for r in conn.execute(
                "SELECT source_id, target_id, relation FROM graph_edges")}
        finally:
            conn.close()

    def test_graph_only_build_preserves_semantic_rows_and_their_generation(self):
        self._seed()
        self._run_build(full=True)
        conn = self._conn()
        try:
            docs_before = conn.execute("SELECT COUNT(*) FROM chunks_docs").fetchone()[0]
            code_before = conn.execute("SELECT COUNT(*) FROM chunks_code").fetchone()[0]
        finally:
            conn.close()
        semantic_layers = {k: v for k, v in self.iss.read_build_layer_state(self.index_dir).items()
                           if k in ("docs", "code")}
        gen = self._generation()

        (self.root / "pkg_a" / "lib.py").write_text(
            "def helper(value):\n    return value + 4\n\n\ndef only_graph():\n    return 1\n")
        # `content="graph"` is the graph-only rebuild verb (the MCP surface
        # spells it `index_build(content='graph', mode='rebuild')`).
        result = self._run_build(full=True, content="graph")
        self.assertNotIn("failed", result)

        conn = self._conn()
        try:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM chunks_docs").fetchone()[0], docs_before)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM chunks_code").fetchone()[0], code_before)
        finally:
            conn.close()
        self.assertIn("pkg_a/lib.py::only_graph", self._node_ids())

        layers = self.iss.read_build_layer_state(self.index_dir)
        self.assertEqual(layers["graph"]["generation"], self._generation())
        self.assertEqual(layers["graph"]["status"], "published")
        self.assertGreater(self._generation(), gen)
        for layer, row in semantic_layers.items():
            self.assertEqual(
                layers[layer], row,
                f"a graph-only build must not advertise {layer} freshness it did not establish",
            )

    def test_semantic_only_publication_marks_the_graph_stale(self):
        """The decision is one function, so it reads the same in both build
        paths: a build that publishes semantic rows while the graph's SOURCE
        inputs changed and the graph itself was not published marks the graph
        stale rather than leaving it readable as current."""
        state = self.bi._layer_publication_state(
            build_docs=True, build_code=True,
            graph_published=False, graph_sources_changed=True)
        self.assertEqual(state, {"docs": self.bi.LAYER_PUBLISHED,
                                 "code": self.bi.LAYER_PUBLISHED,
                                 "graph": self.bi.LAYER_STALE})
        # Unchanged graph sources leave the graph row alone entirely.
        self.assertEqual(
            self.bi._layer_publication_state(
                build_docs=True, build_code=False,
                graph_published=False, graph_sources_changed=False),
            {"docs": self.bi.LAYER_PUBLISHED},
        )
        # A graph-only build claims only the graph.
        self.assertEqual(
            self.bi._layer_publication_state(
                build_docs=False, build_code=False,
                graph_published=True, graph_sources_changed=True),
            {"graph": self.bi.LAYER_PUBLISHED},
        )

        # And the stale marker really lands through a build.
        self._seed()
        self._run_build(full=True)
        (self.root / "pkg_a" / "lib.py").write_text("def helper(v):\n    return v + 7\n")
        with patch.object(self.bi, "_build_graph_artifacts", return_value={
            "graph_payload": None, "cluster_payload": None,
            "publication": None, "cluster_recomputed": False,
        }):
            result = self._run_build()
        self.assertNotIn("failed", result)
        layers = self.iss.read_build_layer_state(self.index_dir)
        self.assertEqual(layers["graph"]["status"], self.bi.LAYER_STALE)
        self.assertEqual(layers["docs"]["status"], self.bi.LAYER_PUBLISHED)
        self.assertEqual(layers["docs"]["generation"], self._generation())

    def test_rename_removal_and_restoration_keep_cross_file_relationships(self):
        """The doc is the UNCHANGED caller: it references the module by path
        across a rename, a removal and a restoration, and its cross-file edge
        must follow the real corpus each time -- present, invalidated, present
        -- while the per-file row ownership moves with the file."""
        self._seed()
        self._run_build(full=True)
        doc_edge = ("docs/guide.md", "pkg_a/lib.py", "doc_references_code")
        self.assertIn(doc_edge, self._edges())
        self.assertIn("pkg_a/lib.py::helper", self._node_ids())

        def manifest():
            conn = self._conn()
            try:
                return {str(r[0]) for r in conn.execute("SELECT path FROM graph_file_state")}
            finally:
                conn.close()

        def owners():
            conn = self._conn()
            try:
                return {str(r[0]) for r in conn.execute(
                    "SELECT DISTINCT source_file FROM graph_nodes")}
            finally:
                conn.close()

        self.assertIn("pkg_a/lib.py", manifest())

        # RENAME: rows, extraction state and the doc's edge all move off the
        # old path. The doc itself is never re-authored.
        (self.root / "pkg_a" / "lib.py").rename(self.root / "pkg_a" / "lib2.py")
        self._run_build()
        ids = self._node_ids()
        self.assertNotIn("pkg_a/lib.py::helper", ids)
        self.assertIn("pkg_a/lib2.py::helper", ids)
        self.assertNotIn("pkg_a/lib.py", manifest(), "the renamed-away file's state is retired")
        self.assertIn("pkg_a/lib2.py", manifest())
        self.assertNotIn("pkg_a/lib.py", owners(), "no row may keep the retired owner")
        self.assertNotIn(doc_edge, self._edges(),
                         "the unchanged doc's reference into the old path is invalidated")

        # REMOVAL: every row the file owned goes with it.
        (self.root / "pkg_a" / "lib2.py").unlink()
        self._run_build()
        self.assertNotIn("pkg_a/lib2.py::helper", self._node_ids())
        self.assertNotIn("pkg_a/lib2.py", manifest())
        self.assertNotIn("pkg_a/lib2.py", owners())

        # RESTORATION: the original path comes back and so does the edge the
        # unchanged doc always claimed.
        (self.root / "pkg_a" / "lib.py").write_text("def helper(value):\n    return value + 1\n")
        self._run_build()
        self.assertIn("pkg_a/lib.py::helper", self._node_ids())
        self.assertIn("pkg_a/lib.py", manifest())
        self.assertIn(doc_edge, self._edges(),
                      "restoring the target must restore the unchanged doc's edge")

    def test_reused_clusters_publish_no_artifact_and_no_retired_folder(self):
        """The fingerprint gate reuses the previous generation's communities.

        Wave 1xny6 lane L6b retired the derived cluster artifact this used to
        watch for an mtime move: there is no file to rewrite, and a reused
        generation must not conjure the retired folder back into existence.
        """
        self._seed()
        self._run_build(full=True)
        retired = self.index_dir / "graph"
        self.assertFalse(retired.exists())
        # A body-only edit: the node/edge SET (and therefore the graph
        # fingerprint) is unchanged, so the clusters are reused.
        (self.root / "pkg_a" / "lib.py").write_text(
            "def helper(value):\n    return value + 99\n")
        result = self._run_build()
        self.assertNotIn("failed", result)
        self.assertFalse(retired.exists(),
                         "a reused-cluster build recreated the retired graph folder")

    def _strand_graph_path(self, rel: str) -> None:
        """Leave a graph row whose file AND bookkeeping entry are gone.

        The walk then sees no change, so the build takes the ZERO-CHANGE seam
        and the orphan reconcile is the only thing with work to do -- which is
        the idle publication path.
        """
        meta = _read_meta_store(self.index_dir)
        fm = meta.get("file_meta") or {}
        fm.pop(rel, None)
        (self.root / rel).unlink()
        meta["file_meta"] = fm
        _seed_meta_store(self.index_dir, meta)

    def test_idle_publication_refuses_a_superseded_attempt(self):
        """The idle pass carries the same in-transaction fence as the build
        path: a rival attempt recorded before the commit stops the graph
        retirement from publishing."""
        self._seed()
        (self.root / "pkg_a" / "orphan.py").write_text("def orphaned_symbol():\n    return 1\n")
        self._run_build(full=True)
        self.assertIn("pkg_a/orphan.py::orphaned_symbol", self._node_ids())
        self._strand_graph_path("pkg_a/orphan.py")
        # Only the GRAPH participants: the canonical semantic reap is a
        # separate, already-committed step of the idle pass, so its rows move
        # regardless of whether the graph publication lands.
        def graph_census():
            return {k: v for k, v in self._census().items() if k.startswith("graph_")}

        before, gen = graph_census(), self._generation()

        # The idle pass prepares its retirement inside
        # `_execute_orphan_store_reconcile`, so the rival lands right after
        # that and before the idle transaction opens.
        state = {"fired": 0}
        real = self.bi._execute_orphan_store_reconcile

        def _wrapped(*args, **kwargs):
            out = real(*args, **kwargs)
            state["fired"] += 1
            other = self.iss._full_durable_connection(self.index_dir)
            try:
                with other:
                    other.execute(
                        "UPDATE build_state SET attempt_id='rival-idle', "
                        "status='building' WHERE id=1")
            finally:
                other.close()
            return out

        with patch.object(self.bi, "_execute_orphan_store_reconcile", _wrapped), \
                redirect_stderr(io.StringIO()):
            result = self._run_build()
        self.assertEqual(state["fired"], 1, "precondition: the idle pass prepared a retirement")
        self.assertTrue(result.get("failed"), result)
        self.assertIn("no longer current", result.get("failure", ""), result)
        self.assertEqual(graph_census(), before,
                         "a superseded idle attempt must publish no graph rows")
        self.assertEqual(self._generation(), gen)
        self.assertIn("pkg_a/orphan.py::orphaned_symbol", self._node_ids(),
                      "the previous generation's rows are untouched")

    def test_build_path_orphan_seam_never_runs_a_second_graph_merge(self):
        """On the build path the graph merge has already retired every
        known-minus-current path in its PREPARED (uncommitted) plan. Running
        the orphan seam's retirement merge as well would prepare a rival plan
        from pre-publication state and overwrite this build's edits."""
        self._seed()
        (self.root / "pkg_a" / "orphan.py").write_text("def orphaned_symbol():\n    return 1\n")
        self._run_build(full=True)
        self._strand_graph_path("pkg_a/orphan.py")
        # A REAL edit in the same build, so the build path (not the idle seam) runs.
        (self.root / "pkg_a" / "lib.py").write_text(
            "def helper(value):\n    return value + 5\n\n\ndef fresh_symbol():\n    return 7\n")

        gi = self.bi._get_graph_indexer()
        with patch.object(gi, "retire_orphaned_graph_paths",
                          side_effect=AssertionError("second graph merge at the build seam")), \
                redirect_stderr(io.StringIO()):
            result = self._run_build()
        self.assertNotIn("failed", result)
        ids = self._node_ids()
        self.assertIn("pkg_a/lib.py::fresh_symbol", ids, "this build's edit must publish")
        self.assertNotIn("pkg_a/orphan.py::orphaned_symbol", ids,
                         "the stranded path is retired by the merge that published")
        self.assertEqual((result.get("orphan_rows_reconciled") or {}).get("graph"), 1)

    def test_mtime_only_change_reuses_vectors_and_graph_rows(self):
        self._seed()
        self._run_build(full=True)
        import sqlite_vector_store as vectors

        before_vectors = vectors.payload_rows(self.index_dir, "code", include_vector=True)
        conn = self._conn()
        try:
            before_nodes = sorted(conn.execute(
                "SELECT node_id, attributes FROM graph_nodes ORDER BY node_id"))
            before_fragments = sorted(
                (str(r[0]), str(r[1]), bytes(r[2]))
                for r in conn.execute("SELECT path, name, fragment FROM graph_merge_state"))
        finally:
            conn.close()

        for rel in ("pkg_a/lib.py", "pkg_a/caller.py", "docs/guide.md"):
            os.utime(self.root / rel, None)
        result = self._run_build()
        self.assertTrue(result.get("up_to_date"), result)

        self.assertEqual(vectors.payload_rows(self.index_dir, "code", include_vector=True),
                         before_vectors, "an mtime-only touch must reuse every vector")
        conn = self._conn()
        try:
            self.assertEqual(sorted(conn.execute(
                "SELECT node_id, attributes FROM graph_nodes ORDER BY node_id")), before_nodes)
            self.assertEqual(sorted(
                (str(r[0]), str(r[1]), bytes(r[2]))
                for r in conn.execute("SELECT path, name, fragment FROM graph_merge_state")),
                before_fragments, "an mtime-only touch must reuse every graph fragment")
        finally:
            conn.close()

class EpochOrderingAndFaultTests(_EpochBuildCase):
    """AC-3/AC-7 core matrix: fence-first ordering, structured no-fallback
    failures at every mandatory boundary, generation semantics, and the
    standalone FTS-rebuild/optimize writers."""

    def test_true_noop_never_opens_the_epoch(self):
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        self._run_build(full=True)
        gen = self._generation()
        tok = self.iss.build_epoch_token(self.index_dir)
        result = self.bi.build_index(self.root, full=False, content="all", verbose=False)
        self.assertTrue(result["up_to_date"])
        self.assertEqual(self._generation(), gen,
                         "a proven true no-op must leave the generation unchanged")
        self.assertEqual(self.iss.build_epoch_token(self.index_dir), tok)

    def test_fence_failure_is_a_structured_build_failure(self):
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        store = self.bi._get_index_state_store()
        with patch.object(store, "begin_recoverable_build_epoch", side_effect=RuntimeError("fence write failed")):
            result = self._run_build(full=True)
        self.assertTrue(result.get("failed"))
        self.assertIn("could not open the build epoch", result["failure"])
        self.assertIsNone(self.iss.build_epoch_token(self.index_dir))

    def test_bookkeeping_failure_leaves_epoch_incomplete(self):
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        store = self.bi._get_index_state_store()
        with patch.object(store, "write_build_bookkeeping_locked", side_effect=RuntimeError("locked")):
            result = self._run_build(full=True)
        self.assertTrue(result.get("failed"))
        self.assertIn("Atomic semantic publication failed", result["failure"])
        state = self.iss.read_build_state(self.index_dir)
        self.assertEqual(state["status"], "building",
                         "a swallowed mandatory-resident failure must not publish")
        self.assertIsNone(self.iss.build_epoch_token(self.index_dir))

    def test_prepared_source_change_rolls_back_complete_semantic_delta(self):
        import sqlite_vector_store as vectors
        _make_repo(self.root, {"src/foo.py": "def f(): return 1\n"})
        self._run_build(full=True)
        before = vectors.payload_rows(self.index_dir, "code", include_vector=True)
        old_meta = self.iss.export_meta_snapshot(self.index_dir)
        source = self.root / "src/foo.py"
        source.write_text("def f(): return 2\n")
        original_apply = vectors.PreparedUpdates.apply
        mutations = []
        def change_during_publication(prepared, store, **kwargs):
            original_apply(prepared, store, **kwargs)
            mutations.append(len(mutations) + 3)
            source.write_text(f"def f(): return {mutations[-1]}\n")
        with patch.object(vectors.PreparedUpdates, "apply", change_during_publication):
            result = self._run_build(full=False)
        self.assertTrue(result.get("failed"))
        self.assertIn("Source changed during embedding", result["failure"])
        self.assertEqual(vectors.payload_rows(self.index_dir, "code", include_vector=True), before)
        self.assertEqual(self.iss.export_meta_snapshot(self.index_dir), old_meta)
        self.assertIsNotNone(self.iss.build_epoch_token(self.index_dir))
        self.assertEqual(mutations, [3, 4])
        self.assertFalse(self._run_build(full=False).get("failed"))
        self.assertTrue(any("return 4" in row["text"] for row in vectors.payload_rows(
            self.index_dir, "code", predicate="path = 'src/foo.py'")))

    def test_prepared_model_change_refuses_publication(self):
        import sqlite_vector_store as vectors
        _make_repo(self.root, {"src/foo.py": "def f(): return 1\n"})
        self._run_build(full=True)
        before = vectors.payload_rows(self.index_dir, "code", include_vector=True)
        (self.root / "src/foo.py").write_text("def f(): return 2\n")
        original_apply = vectors.PreparedUpdates.apply
        original_model = self.bi.CODE_MODEL
        def change_model(prepared, store, **kwargs):
            original_apply(prepared, store, **kwargs)
            self.bi.CODE_MODEL = "changed-during-publication"
        try:
            with patch.object(vectors.PreparedUpdates, "apply", change_model):
                result = self._run_build(full=False)
        finally:
            self.bi.CODE_MODEL = original_model
        self.assertTrue(result.get("failed"))
        self.assertIn("Model/chunker/configuration changed", result["failure"])
        self.assertEqual(vectors.payload_rows(self.index_dir, "code", include_vector=True), before)
        self.assertIsNone(self.iss.build_epoch_token(self.index_dir))

    def test_removed_source_reappearing_before_publication_reprepares_before_apply(self):
        import sqlite_vector_store as vectors
        _make_repo(self.root, {"src/victim.py": "def victim(): return 1\n",
                               "src/other.py": "def other(): return 1\n"})
        self._run_build(full=True)
        victim = self.root / "src/victim.py"
        victim.unlink()
        (self.root / "src/other.py").write_text("def other(): return 2\n")
        original_reap = self.bi._reap_stranded_vector_rows
        original_apply = vectors.PreparedUpdates.apply
        calls = []
        def reappear_after_planning(*args, **kwargs):
            result = original_reap(*args, **kwargs)
            if not victim.exists():
                victim.write_text("def victim(): return 3\n")
            return result
        def apply(prepared, store, **kwargs):
            calls.append(1)
            return original_apply(prepared, store, **kwargs)
        with patch.object(self.bi, "_reap_stranded_vector_rows", reappear_after_planning), \
                patch.object(vectors.PreparedUpdates, "apply", apply):
            result = self._run_build(full=False)
        self.assertFalse(result.get("failed"))
        self.assertEqual(len(calls), 1, "refused first attempt must never apply")
        self.assertTrue(any("return 3" in row["text"] for row in vectors.payload_rows(
            self.index_dir, "code", predicate="path = 'src/victim.py'")))

    def test_removed_source_reappearing_after_apply_rolls_back_then_retries(self):
        import sqlite_vector_store as vectors
        for full in (False, True):
            with self.subTest(full=full):
                _make_repo(self.root, {"src/victim.py": "def victim(): return 1\n",
                                       "src/other.py": "def other(): return 1\n"})
                self._run_build(full=True)
                before = vectors.payload_rows(self.index_dir, "code", include_vector=True)
                victim = self.root / "src/victim.py"
                victim.unlink()
                (self.root / "src/other.py").write_text("def other(): return 2\n")
                original_apply = vectors.PreparedUpdates.apply
                calls = []
                def reappear_after_apply(prepared, store, **kwargs):
                    if calls:
                        self.assertEqual(vectors.payload_rows(self.index_dir, "code", include_vector=True), before,
                                         "the first attempt must roll back before retry")
                    calls.append(1)
                    original_apply(prepared, store, **kwargs)
                    if len(calls) == 1:
                        victim.write_text("def victim(): return 3\n")
                with patch.object(vectors.PreparedUpdates, "apply", reappear_after_apply):
                    result = self._run_build(full=full)
                self.assertFalse(result.get("failed"))
                self.assertEqual(len(calls), 2)
                self.assertIsNotNone(self.iss.build_epoch_token(self.index_dir))
                self.assertTrue(any("return 3" in row["text"] for row in vectors.payload_rows(
                    self.index_dir, "code", predicate="path = 'src/victim.py'")))

    def test_removal_guard_preserves_explicit_scope_and_excluded_code(self):
        _make_repo(self.root, {"tests/test_victim.py": "def test_victim(): pass\n",
                               "src/omitted.py": "def omitted(): pass\n"})
        kwargs = dict(respect_ignore=True, include_prefixes=(), project_include_prefixes=(),
                      include_tests=False, include_generated=False)
        self.bi._validate_prepared_removals(
            self.root, self.index_dir, {"src/omitted.py"}, {"code": {"tests/test_victim.py"}},
            requested_files=(Path("tests/test_victim.py"),), **kwargs)
        with self.assertRaisesRegex(RuntimeError, "Removal source changed"):
            self.bi._validate_prepared_removals(
                self.root, self.index_dir, {"src/omitted.py"}, {}, requested_files=None, **kwargs)

    def test_missing_canonical_layer_is_rebuilt_despite_surviving_other_layer(self):
        import sqlite_vector_store as vectors
        _make_repo(self.root, {"src/foo.py": 'def f():\n    """Shared docs marker."""\n    return 1\n'})
        self._run_build(full=True)
        before = vectors.payload_rows(self.index_dir, "docs", predicate="path = 'src/foo.py'", include_vector=True)
        self.assertTrue(before)
        store = self.iss.IndexStateStore(self.index_dir)
        try:
            # Simulate a lost canonical layer with retained old bookkeeping.
            # The surviving code rows must not hide its docs-layer hole.
            with store._conn:
                store._conn.execute("DELETE FROM chunks_docs WHERE path=?", ("src/foo.py",))
        finally:
            store.close()
        result = self._run_build(full=False)
        self.assertFalse(result.get("failed"))
        after = vectors.payload_rows(self.index_dir, "docs", predicate="path = 'src/foo.py'", include_vector=True)
        self.assertEqual(after, before)
        self.assertIsNotNone(self.iss.build_epoch_token(self.index_dir))

    def test_mandatory_reconcile_failure_blocks_publication(self):
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        with patch.object(self.bi, "_sync_chunk_derived_state",
                          return_value={"code": {"error": "fts write failed"}}):
            result = self._run_build(full=True)
        self.assertTrue(result.get("failed"))
        self.assertIsNone(self.iss.build_epoch_token(self.index_dir))

    def test_finalize_cas_miss_is_a_failed_publication(self):
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        store = self.bi._get_index_state_store()
        with patch.object(store, "finalize_build_epoch", return_value=False):
            result = self._run_build(full=True)
        self.assertTrue(result.get("failed"))
        self.assertIsNone(self.iss.build_epoch_token(self.index_dir))

    def test_recovery_after_failure_heals_idempotently(self):
        """Bounded retry contract: after an injected failure the NEXT ordinary
        build converges — no manual repair step, no false completion left over."""
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        store = self.bi._get_index_state_store()
        with patch.object(store, "write_build_bookkeeping_locked", side_effect=RuntimeError("locked")):
            self._run_build(full=True)
        self.assertIsNone(self.iss.build_epoch_token(self.index_dir))
        result = self._run_build(full=False)
        self.assertFalse(result.get("failed"))
        self.assertIsNotNone(self.iss.build_epoch_token(self.index_dir))

    def test_standalone_fts_rebuild_holds_its_own_epoch(self):
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        self._run_build(full=True)
        gen = self._generation()
        with contextlib.redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            stats = self.bi.rebuild_derived_chunk_state(self.index_dir, verbose=False)
        self.assertNotIn("error", stats)
        self.assertEqual(self._generation(), gen + 1)
        self.assertIsNotNone(self.iss.build_epoch_token(self.index_dir))

    def test_optimize_holds_its_own_epoch(self):
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        self._run_build(full=True)
        gen = self._generation()
        with contextlib.redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            results = self.bi.optimize_index_tables(self.index_dir)
        self.assertNotIn("error", results)
        self.assertNotIn("finalize", results)
        self.assertEqual(self._generation(), gen + 1)
        self.assertIsNotNone(self.iss.build_epoch_token(self.index_dir))


    def test_scoped_build_refuses_unproven_populated_store(self):
        """Review refutation: a scoped build over a reset store (Lance tables
        present, no provenance) must escalate to all-layer convergence — it
        may not publish `complete` around the unprovenanced table."""
        _make_repo(self.root, {
            "src/foo.py": "def f(): return 1\n",
            "docs/guide.md": "## Intro\n\nHello.\n",
        })
        self._run_build(full=True)
        store=self.iss.IndexStateStore(self.index_dir)
        with store._conn:
            store._conn.execute("DELETE FROM build_layer_meta")
            store._conn.execute("DELETE FROM layer_path_state")
        store.close()
        # Missing provenance in a populated completed index is now explicitly
        # unproven: neither a scoped nor a full build may silently bless it.
        import index_compatibility
        token = self.iss.build_epoch_token(self.index_dir)
        with patch.object(self.bi, "_get_embedder") as embedder:
            with self.assertRaises(index_compatibility.IndexCompatibilityError) as raised:
                self.bi.build_index(self.root, full=False, content="docs", verbose=False)
        self.assertEqual(raised.exception.code, "index_compatibility_unproven")
        embedder.assert_not_called()
        self.assertEqual(token, self.iss.build_epoch_token(self.index_dir))

    def test_unknown_schema_is_preserved_before_any_build_decision(self):
        _make_repo(self.root, {'src/foo.py':'def f(): return 1\n','docs/guide.md':'## Intro\nHello.\n'})
        self._run_build(full=True)
        store=self.iss.IndexStateStore(self.index_dir)
        before=store._conn.execute('SELECT COUNT(*) FROM vectors_code').fetchone()[0]
        with store._conn:
            store._conn.execute("UPDATE meta SET value='999' WHERE key='store_schema_version'")
        with patch.object(self.bi,'_get_embedder') as embedder:
            result=self.bi.build_index(self.root,full=True,content='all')
        self.assertTrue(result.get('failed'))
        self.assertIn('storage_schema_unsupported: 999',result['failure'])
        embedder.assert_not_called()
        self.assertEqual(store._conn.execute('SELECT COUNT(*) FROM vectors_code').fetchone()[0],before)
        self.assertEqual(store._conn.execute("SELECT value FROM meta WHERE key='store_schema_version'").fetchone(),('999',))
        store.close()

    def test_completion_rear_guard_is_wired_before_finalize(self):
        """Source pin for the rear guard: the unprovenanced-table verification
        sits between the bookkeeping write and the finalize CAS."""
        src = (SCRIPTS_ROOT / "indexer.py").read_text(encoding="utf-8")
        bookkeeping = src.index("write_build_bookkeeping_locked(conn,new_meta)")
        guard = src.index("_unprovenanced_at_publish", bookkeeping)
        finalize = src.index("finalize_build_epoch(index_dir, _build_attempt)", guard)
        self.assertGreater(finalize, guard)

    def test_fts_rebuild_refuses_without_completed_epoch(self):
        """Review refutation (empty-FTS false completion): the derived rebuild
        may only RESTORE readiness — on an uninitialized or building store it
        refuses and never manufactures a complete epoch."""
        self.index_dir.mkdir(parents=True, exist_ok=True)
        stats = self.bi.rebuild_derived_chunk_state(self.index_dir, verbose=False)
        self.assertIn("no completed build epoch", stats.get("error", ""))
        self.assertIsNone(self.iss.build_epoch_token(self.index_dir))
        # Same over a mid-build (building) store.
        self.iss.begin_build_epoch(self.index_dir, "in-flight")
        stats2 = self.bi.rebuild_derived_chunk_state(self.index_dir, verbose=False)
        self.assertIn("no completed build epoch", stats2.get("error", ""))
        self.assertIsNone(self.iss.build_epoch_token(self.index_dir))

    def test_optimize_refuses_without_completed_epoch(self):
        with tempfile.TemporaryDirectory() as td:
            index_dir = Path(td)
            store=self.iss.IndexStateStore(index_dir)
            store.close()
            results = self.bi.optimize_index_tables(index_dir, ("docs",))
            self.assertIn("no completed build epoch", results.get("error", ""))
            self.assertIsNone(self.iss.build_epoch_token(index_dir))

    def test_optimize_error_does_not_finalize_readiness(self):
        """Review refutation: a Tier-3/error reclaim result leaves the epoch
        un-finalized — readers fail closed instead of trusting an in-place
        rewrite that ended in unknown state."""
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        self._run_build(full=True)
        gen = self._generation()

        class _BrokenTable:
            def count_rows(self):
                raise RuntimeError("unreadable")
            def to_arrow(self):
                raise RuntimeError("unreadable")

        class _BrokenDB:
            def open_table(self, name):
                raise RuntimeError("unreadable")

        with patch.object(self.bi._get_index_state_store(), "optimize_state_stores", return_value={"index-state":{"error":"unreadable","integrity":"structural-fail"}}):
            results = self.bi.optimize_index_tables(self.index_dir)
        self.assertIn("finalize", results)
        self.assertIn("NOT finalized", results["finalize"]["error"])
        # Fail-closed: no complete token, generation not advanced.
        self.assertIsNone(self.iss.build_epoch_token(self.index_dir))
        self.assertEqual(self._generation(), gen)
        # And an ordinary rebuild restores readiness afterwards.
        (self.root / "src" / "foo.py").write_text("def f(): return 2\n", encoding="utf-8")
        recover = self._run_build(full=False)
        self.assertFalse(recover.get("failed"))
        self.assertIsNotNone(self.iss.build_epoch_token(self.index_dir))

    def test_unchanged_retry_heals_a_dirty_epoch(self):
        """Review refutation (dirty-epoch unchanged-retry lockout): zero
        changes + a `building` epoch must run recovery and republish — never
        report up_to_date over a permanently failed-closed store."""
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        self._run_build(full=True)
        gen = self._generation()
        # Simulate a builder that died between fence and finalize.
        self.iss.begin_build_epoch(self.index_dir, "code:crashed")
        self.assertIsNone(self.iss.build_epoch_token(self.index_dir))
        with redirect_stderr(io.StringIO()) as err:
            result = self.bi.build_index(self.root, full=False, content="all", verbose=False)
        self.assertTrue(result["up_to_date"])
        self.assertIn("zero-change recovery", err.getvalue())
        # Readiness restored: complete token, generation advanced past the crash.
        self.assertIsNotNone(self.iss.build_epoch_token(self.index_dir))
        self.assertGreater(self._generation(), gen)
        # A second unchanged run over the now-complete epoch is a TRUE no-op.
        gen2 = self._generation()
        result2 = self.bi.build_index(self.root, full=False, content="all", verbose=False)
        self.assertTrue(result2["up_to_date"])
        self.assertEqual(self._generation(), gen2)

    def test_recovery_refuses_when_claimed_table_is_missing(self):
        """Independent-review F1: zero-change recovery must not republish a
        canonical state that claims a layer whose vectors are gone — it
        resets that layer's state and fails visibly; the next ordinary build
        reconstructs the table and only then restores readiness."""
        _make_repo(self.root, {
            "src/foo.py": "def f(): return 1\n",
            "docs/guide.md": "## Intro\n\nHello.\n",
        })
        self._run_build(full=True)
        # Crash simulation + out-of-band table loss for a layer with
        # registry rows. Scoped content='code' is the reviewer's exact
        # reproduction: docs drift-candidacy is out of scope there, so only
        # the recovery guard stands between the loss and republication.
        self.iss.begin_build_epoch(self.index_dir, "code:crashed")
        import shutil
        store=self.iss.IndexStateStore(self.index_dir)
        store._conn.execute("DELETE FROM vectors_docs")
        store.close()
        with redirect_stderr(io.StringIO()):
            result = self.bi.build_index(self.root, full=False, content="code", verbose=False)
        self.assertTrue(result.get("failed"))
        self.assertIn("vector layer is missing", result["failure"])
        self.assertIsNone(self.iss.build_epoch_token(self.index_dir),
                          "recovery must not publish over a missing claimed table")
        # The reset layer state makes the next ordinary build reconstruct.
        docs_mock = _make_embedder_mock(dim=4)
        code_mock = _make_embedder_mock(dim=4)
        with redirect_stderr(io.StringIO()), \
             patch.object(self.bi, "_get_embedder", side_effect=[docs_mock, code_mock]):
            recover = self.bi.build_index(self.root, full=False, content="all", verbose=False)
        self.assertFalse(recover.get("failed"))
        self.assertTrue(self.bi.vector_store.layer_available(self.index_dir,"docs"))
        self.assertIsNotNone(self.iss.build_epoch_token(self.index_dir))

    def test_cli_exits_nonzero_on_structured_failure(self):
        """Review refutation: a {failed: true} build must exit 1 through the
        CLI so setup/MCP subprocess callers see the failure."""
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        with patch.object(self.bi, "build_index",
                          return_value={"failed": True, "failure": "injected"}), \
             redirect_stderr(io.StringIO()) as err:
            rc = self.bi.main(["--root", str(self.root), "--content", "all"])
        self.assertEqual(rc, 1)
        self.assertIn("injected", err.getvalue())
        with patch.object(self.bi, "build_index", return_value={"up_to_date": True}):
            self.assertEqual(self.bi.main(["--root", str(self.root), "--content", "all"]), 0)

    def test_fresh_process_kill_between_fence_and_finalize_fails_closed(self):
        """AC-7/AC-9 kill fixture: a builder killed after the durable fence
        leaves building/no-token for a FRESH process; the next ordinary build
        restores readiness."""
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        self._run_build(full=True)
        gen = self._generation()
        script = (
            "import sys, os\n"
            f"sys.path.insert(0, {str(SCRIPTS_ROOT)!r})\n"
            "from pathlib import Path\n"
            "import importlib.util\n"
            f"spec = importlib.util.spec_from_file_location('iss', {str(SCRIPTS_ROOT / 'index_state_store.py')!r})\n"
            "mod = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(mod)\n"
            f"mod.begin_build_epoch(Path({str(self.index_dir)!r}), 'kill:test')\n"
            "os._exit(9)\n"
        )
        proc = subprocess.run([sys.executable, "-c", script], capture_output=True)
        self.assertEqual(proc.returncode, 9)
        # Fresh reader view: interrupted build = building + fail-closed token.
        state = self.iss.read_build_state(self.index_dir)
        self.assertEqual(state["status"], "building")
        self.assertIsNone(self.iss.build_epoch_token(self.index_dir))
        # Ordinary recovery: the next mutating build supersedes the dead
        # attempt and publishes a fresh complete epoch.
        (self.root / "src" / "foo.py").write_text("def f(): return 9\n", encoding="utf-8")
        result = self._run_build(full=False)
        self.assertFalse(result.get("failed"))
        self.assertIsNotNone(self.iss.build_epoch_token(self.index_dir))
        self.assertGreater(self._generation(), gen)


class MemoryGenerationGateTests(unittest.TestCase):
    """Round-4 P2: the memory-generation bump is gated on changed/removed
    memory records, not on any record existing in the build."""

    def setUp(self):
        self.bi = load_build_index()

    def test_only_changed_or_removed_memory_records_trigger(self):
        f = self.bi._memory_record_touched
        # No memory path in the changed/removed sets → no bump.
        self.assertFalse(f({"src/a.py", "docs/guide.md"}, set()))
        self.assertFalse(f(set(), set()))
        # The schema README is not a record.
        self.assertFalse(f({"docs/agents/memory/README.md"}, {"docs/agents/memory/README.md"}))
        # A changed record → bump.
        self.assertTrue(f({"docs/agents/memory/mem-x.md"}, set()))
        # A removed record → bump (delete coverage).
        self.assertTrue(f(set(), {"docs/agents/memory/mem-y.md"}))
        # Windows-style separators normalize.
        self.assertTrue(f({"docs\\agents\\memory\\mem-z.md"}, set()))


class MemoryInvalidationBuildTailTests(unittest.TestCase):
    """Round-4 re-review P1 evidence gap: exercise memory invalidation through
    the REAL ``build_index`` path (not the helper/manual primitive) across the
    add / edit / delete / no-op / unrelated / README matrix, plus the forced
    late-failure and forced advance-failure (fail-closed) cases."""

    _REC = (
        "# Lesson\n\nOwner: Engineering\nStatus: active\nLast verified: 2026-07-13\n\n"
        "Memory ID: `mem-a`\nKind: `decision`\nConfidence: 0.7\n"
        "Created: 2026-07-13\nUpdated: 2026-07-13\n\n"
        "## Summary\n\n{body}\n\n## Evidence\n\n- `1x`\n\n## Targets\n\n- `src/foo.py`\n"
    )

    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.index_dir = self.root / ".wavefoundry" / "index"
        self.rec = self.root / "docs" / "agents" / "memory" / "mem-a.md"
        self.rec_rel = "docs/agents/memory/mem-a.md"

    def _run_build(self, full: bool = False):
        docs_mock = _make_embedder_mock(dim=4)
        code_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", side_effect=[docs_mock, code_mock]):
            return self.bi.build_index(self.root, full=full, content="all", verbose=False)

    def _generation(self) -> int:
        state = _store_mod().read_memory_state(self.index_dir)
        return int(state["generation"]) if state else 0

    def _seed(self, body: str = "First body."):
        _make_repo(self.root, {
            "src/foo.py": "def f():\n    return 1\n",
            "docs/agents/memory/README.md": "# Memory records\n\nSchema doc.\n",
        })
        self.rec.parent.mkdir(parents=True, exist_ok=True)
        self.rec.write_text(self._REC.format(body=body), encoding="utf-8")
        self._run_build(full=True)  # first build advances (record is 'added')

    def test_edit_advances_generation(self):
        self._seed()
        before = self._generation()
        self.rec.write_text(self._REC.format(body="Edited body."), encoding="utf-8")
        self._run_build()
        self.assertGreater(self._generation(), before, "a record edit must advance the generation")

    def test_delete_advances_generation(self):
        self._seed()
        before = self._generation()
        self.rec.unlink()
        self._run_build()
        self.assertGreater(self._generation(), before, "a record delete must advance the generation")

    def test_add_advances_generation(self):
        # Seed WITHOUT the record, then add it on an incremental build.
        _make_repo(self.root, {"src/foo.py": "def f():\n    return 1\n"})
        self._run_build(full=True)
        before = self._generation()
        self.rec.parent.mkdir(parents=True, exist_ok=True)
        self.rec.write_text(self._REC.format(body="New."), encoding="utf-8")
        self._run_build()
        self.assertGreater(self._generation(), before, "a new record must advance the generation")

    def test_noop_build_does_not_advance(self):
        self._seed()
        before = self._generation()
        result = self.bi.build_index(self.root, full=False, content="all", verbose=False)
        self.assertTrue(result["up_to_date"])
        self.assertEqual(self._generation(), before, "a true no-op must not advance the generation")

    def test_unrelated_change_does_not_advance(self):
        self._seed()
        before = self._generation()
        (self.root / "src" / "foo.py").write_text("def f():\n    return 2\n", encoding="utf-8")
        self._run_build()
        self.assertEqual(self._generation(), before, "an unrelated code change must not advance memory")

    def test_readme_change_does_not_advance(self):
        self._seed()
        before = self._generation()
        (self.root / "docs" / "agents" / "memory" / "README.md").write_text(
            "# Memory records\n\nSchema doc, revised.\n", encoding="utf-8")
        self._run_build()
        self.assertEqual(self._generation(), before, "the schema README is not a record")

    def test_late_build_failure_still_invalidates(self):
        # memory_invalidate runs BEFORE the semantic build; a later embedder
        # failure that aborts the build must not leave the generation un-advanced.
        self._seed()
        before = self._generation()
        self.rec.write_text(self._REC.format(body="Edited before crash."), encoding="utf-8")

        reached = {"embedder": False}

        def boom(*a, **k):
            reached["embedder"] = True
            raise RuntimeError("forced late build failure")

        with patch.object(self.bi, "_get_embedder", side_effect=boom):
            # Whether build_index re-raises or returns an error result, the
            # semantic work did NOT complete — the generation must still be
            # advanced (memory_invalidate ran before the embedder).
            try:
                self.bi.build_index(self.root, full=False, content="all", verbose=False)
            except Exception:
                pass
        self.assertTrue(reached["embedder"], "the test must actually reach the late embedder step")
        self.assertGreater(self._generation(), before,
                           "invalidation must be independent of later semantic-build success")

    def test_advance_failure_fails_build_before_bookkeeping(self):
        # Round-4 re-review P1: when the generation cannot advance, the build
        # must FAIL before recording file metadata — so the old file_meta is
        # preserved and the recovered retry re-detects the edit. A best-effort
        # fence also makes readers bypass in the meantime.
        self._seed()
        before_meta = dict(_read_meta_store(self.index_dir).get("file_meta", {}))
        iss = self.bi._get_index_state_store()
        self.rec.write_text(self._REC.format(body="Edited, advance will fail."), encoding="utf-8")
        real_adv = iss.memory_advance
        iss.memory_advance = lambda *a, **k: None
        try:
            result = self.bi.build_index(self.root, full=False, content="all", verbose=False)
        finally:
            iss.memory_advance = real_adv
        self.assertTrue(result.get("failed"), "a wedged memory seqlock must fail the build")
        self.assertFalse(result.get("up_to_date"))
        # file_meta preserved (bookkeeping never ran) → the retry re-detects.
        after_meta = _read_meta_store(self.index_dir).get("file_meta", {})
        self.assertEqual(after_meta.get(self.rec_rel), before_meta.get(self.rec_rel),
                         "the edited record's file_meta must NOT be advanced on a failed build")
        # Best-effort fence set → readers bypass in the window.
        self.assertEqual(_store_mod().read_memory_state(self.index_dir)["dirty"], 1)
        # Recovery: advance works again → the retry advances the generation.
        gen_before_retry = self._generation()
        self._run_build()
        self.assertGreater(self._generation(), gen_before_retry,
                           "the recovered retry must re-detect the edit and advance")


class NoOpDriftClearFailureBuildTests(unittest.TestCase):
    """Round-4 re-review (3) P1: a true no-op build whose confirmed git→non-git
    drift clear FAILS must return a structured FAILED build (not up_to_date),
    preserve the stale drift, and let a later retry clear it. Exercised through
    the REAL ``build_index`` no-op path, not the helper."""

    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.index_dir = self.root / ".wavefoundry" / "index"

    def _git(self, *args, ts=None):
        env = dict(os.environ)
        if ts is not None:
            env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = f"{ts} +0000"
        subprocess.run(["git", "-C", str(self.root), *args], check=True, env=env)

    def _run_build(self, full=False):
        docs_mock = _make_embedder_mock(dim=4)
        code_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", side_effect=[docs_mock, code_mock]):
            return self.bi.build_index(self.root, full=full, content="all", verbose=False)

    def _seed_drift_then_drop_git(self):
        import shutil
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self._git("config", "user.email", "t@t")
        self._git("config", "user.name", "t")
        _make_repo(self.root, {
            "src/foo.py": "x = 1\n",
            "docs/g.md": "Status: active\n\nSee `src/foo.py`.\n",
        })
        self._git("add", "-A")
        self._git("commit", "-qm", "c1", ts=1700000000)
        for i in range(3):
            (self.root / "src" / "foo.py").write_text(f"x = {i + 2}\n", encoding="utf-8")
            self._git("add", "-A")
            self._git("commit", "-qm", f"churn{i}", ts=1700000000 + (i + 1) * 1000)
        self._run_build(full=True)  # derives + records drift
        iss = self.bi._get_index_state_store()
        self.assertTrue(iss.doc_drift_for_path(self.index_dir, "docs/g.md"))
        _rmtree_git(self.root / ".git")  # git authority disappears
        return iss

    def test_noop_clear_failure_fails_build_and_retry_recovers(self):
        iss = self._seed_drift_then_drop_git()
        real_ctor = iss.IndexStateStore

        class _BoomStore(real_ctor):
            def clear_attribution_and_drift(self):
                raise RuntimeError("forced clear failure")

        iss.IndexStateStore = _BoomStore
        try:
            result = self.bi.build_index(self.root, full=False, content="all", verbose=False)
        finally:
            iss.IndexStateStore = real_ctor
        self.assertTrue(result.get("failed"),
                        "a no-op whose confirmed-non-git clear fails must fail the build")
        self.assertFalse(result.get("up_to_date"))
        # Stale drift preserved (nothing cleared) — not served behind up_to_date.
        self.assertTrue(iss.doc_drift_for_path(self.index_dir, "docs/g.md"),
                        "the stale drift must survive the failed clear")
        # Retry: clear works → build succeeds and the drift is gone.
        retry = self.bi.build_index(self.root, full=False, content="all", verbose=False)
        self.assertFalse(retry.get("failed"))
        self.assertIsNone(iss.doc_drift_for_path(self.index_dir, "docs/g.md"),
                          "the recovered retry must clear the stale drift")

    def test_noop_clear_success_reports_up_to_date(self):
        # The happy path: a confirmed transition clears cleanly and the no-op
        # still reports up_to_date (no spurious failure).
        iss = self._seed_drift_then_drop_git()
        result = self.bi.build_index(self.root, full=False, content="all", verbose=False)
        self.assertFalse(result.get("failed"))
        self.assertTrue(result.get("up_to_date"))
        self.assertIsNone(iss.doc_drift_for_path(self.index_dir, "docs/g.md"))

    def test_changed_build_clear_failure_fails_and_retry_recovers(self):
        # Round-4 re-review (4) P1: a CHANGED build (reaches the build-tail drift
        # pass, not the no-op path) whose confirmed-non-git clear FAILS must also
        # fail the build BEFORE epoch finalization, preserve the stale drift, and
        # recover on retry.
        iss = self._seed_drift_then_drop_git()
        # Make the build a CHANGED build (edit an unrelated code file).
        (self.root / "src" / "foo.py").write_text("x = 999\n", encoding="utf-8")
        real_ctor = iss.IndexStateStore

        class _BoomStore(real_ctor):
            def clear_attribution_and_drift(self):
                raise RuntimeError("forced clear failure")

        iss.IndexStateStore = _BoomStore
        try:
            result = self._run_build()  # changed build → build-tail drift pass
        finally:
            iss.IndexStateStore = real_ctor
        self.assertTrue(result.get("failed"),
                        "a changed build whose confirmed-non-git clear fails must fail")
        self.assertFalse(result.get("up_to_date"))
        self.assertTrue(iss.doc_drift_for_path(self.index_dir, "docs/g.md"),
                        "the stale drift must survive the failed clear")
        # Retry (clear works) succeeds and clears.
        retry = self._run_build()
        self.assertFalse(retry.get("failed"))
        self.assertIsNone(iss.doc_drift_for_path(self.index_dir, "docs/g.md"))

    def test_ordinary_drift_compute_failure_stays_optional(self):
        # Contract guard: an ordinary drift COMPUTATION failure (not a confirmed
        # transition clear) must remain OPTIONAL — the build still succeeds.
        import shutil
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self._git("config", "user.email", "t@t")
        self._git("config", "user.name", "t")
        _make_repo(self.root, {
            "src/foo.py": "x = 1\n",
            "docs/g.md": "Status: active\n\nSee `src/foo.py`.\n",
        })
        self._git("add", "-A")
        self._git("commit", "-qm", "c1", ts=1700000000)
        self._run_build(full=True)
        iss = self.bi._get_index_state_store()
        # Force the history walk to fail (a compute failure, git still present).
        real = iss._collect_git_history
        iss._collect_git_history = lambda *a, **k: (False, [])
        (self.root / "src" / "foo.py").write_text("x = 2\n", encoding="utf-8")
        try:
            result = self._run_build()
        finally:
            iss._collect_git_history = real
        self.assertFalse(result.get("failed"),
                         "an optional drift-compute failure must not fail the build")


class AmbientGitEnvBuildIsolationTests(unittest.TestCase):
    """Round-4 re-review (6) P1: the FULL build_index derivation (freshness +
    drift + history) must match a clean-environment control EXACTLY even when a
    repository-local git env var (GIT_SHALLOW_FILE) is ambiently set."""

    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.index_dir = self.root / ".wavefoundry" / "index"

    def _git(self, *args, ts=None):
        env = dict(os.environ)
        if ts is not None:
            env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = f"{ts} +0000"
        subprocess.run(["git", "-C", str(self.root), *args], check=True, env=env)

    def _run_build(self, full=False):
        docs_mock = _make_embedder_mock(dim=4)
        code_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", side_effect=[docs_mock, code_mock]):
            return self.bi.build_index(self.root, full=full, content="all", verbose=False)

    def _seed(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self._git("config", "user.email", "t@t")
        self._git("config", "user.name", "t")
        _make_repo(self.root, {
            "src/foo.py": "x = 1\n",
            "docs/g.md": "Status: active\n\nSee `src/foo.py`.\n",
        })
        self._git("add", "-A")
        self._git("commit", "-qm", "c1", ts=1700000000)
        for i in range(3):
            (self.root / "src" / "foo.py").write_text(f"x = {i + 2}\n", encoding="utf-8")
            self._git("add", "-A")
            self._git("commit", "-qm", f"churn{i}", ts=1700000000 + (i + 1) * 1000)

    def _drift_and_freshness(self):
        iss = self.bi._get_index_state_store()
        row = iss.doc_drift_for_path(self.index_dir, "docs/g.md")
        fresh = iss.freshness_for_paths(self.index_dir, ["src/foo.py", "docs/g.md"])
        return row, fresh

    def test_full_build_matches_clean_control_under_git_shallow_file(self):
        # Clean control build.
        self._seed()
        self._run_build(full=True)
        clean_row, clean_fresh = self._drift_and_freshness()
        self.assertEqual(clean_row["commits_since"], 3)
        # Determine a mid-history boundary and set GIT_SHALLOW_FILE ambiently.
        iss = self.bi._get_index_state_store()
        ok, commits = iss._collect_git_history(self.root)
        self.assertTrue(ok)
        shas = [c["sha"] for c in commits]
        shallow = self.root.parent / "shallow-boundary"
        shallow.write_text(shas[len(shas) // 2] + "\n", encoding="utf-8")
        saved = os.environ.get("GIT_SHALLOW_FILE")
        os.environ["GIT_SHALLOW_FILE"] = str(shallow)
        try:
            # A FULL rebuild recomputes everything under the ambient var.
            self._run_build(full=True)
            amb_row, amb_fresh = self._drift_and_freshness()
        finally:
            if saved is None:
                os.environ.pop("GIT_SHALLOW_FILE", None)
            else:
                os.environ["GIT_SHALLOW_FILE"] = saved
        self.assertEqual(amb_row["commits_since"], clean_row["commits_since"],
                         "drift must match the clean control under GIT_SHALLOW_FILE")
        self.assertEqual(amb_row["drifted"], clean_row["drifted"])
        self.assertEqual(amb_fresh, clean_fresh,
                         "freshness must match the clean control under GIT_SHALLOW_FILE")

    def _seed_with_rename(self):
        # Like _seed but the doc points at a RENAMED file, so an ambient
        # diff.renames=false (global config) would change its derived path
        # history / freshness — making the clean-vs-ambient control non-vacuous.
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self._git("config", "user.email", "t@t")
        self._git("config", "user.name", "t")
        _make_repo(self.root, {
            "src/old_name.py": "x = 1\nx = 2\nx = 3\nx = 4\nx = 5\n",
            "docs/g.md": "Status: active\n\nSee `src/new_name.py`.\n",
        })
        self._git("add", "-A")
        self._git("commit", "-qm", "c1", ts=1700000000)
        subprocess.run(["git", "-C", str(self.root), "mv",
                        "src/old_name.py", "src/new_name.py"], check=True)
        self._git("commit", "-qm", "rename", ts=1700001000)

    def test_full_build_matches_clean_control_under_git_config_global(self):
        # Clean control build (git default diff.renames=true).
        self._seed_with_rename()
        self._run_build(full=True)
        iss = self.bi._get_index_state_store()
        clean_hist = [c["files"] for c in iss._collect_git_history(self.root)[1]]
        clean_fresh = iss.freshness_for_paths(
            self.index_dir, ["src/new_name.py", "docs/g.md"])
        clean_row = iss.doc_drift_for_path(self.index_dir, "docs/g.md")
        # Guard: an ambient global diff.renames=false MUST perturb raw git.
        gc = self.root.parent / "gitconfig-global"
        gc.write_text("[diff]\n\trenames = false\n", encoding="utf-8")
        raw = subprocess.run(
            ["git", "-C", str(self.root), "log", "-1", "--name-only", "--format="],
            capture_output=True, text=True,
            env=dict(os.environ, GIT_CONFIG_GLOBAL=str(gc)))
        raw_files = {f.strip() for f in raw.stdout.split() if f.strip()}
        self.assertEqual(raw_files, {"src/old_name.py", "src/new_name.py"},
                         "ambient GIT_CONFIG_GLOBAL must split the rename in raw git")
        # Full rebuild under the ambient global config → identical derivation.
        saved = os.environ.get("GIT_CONFIG_GLOBAL")
        os.environ["GIT_CONFIG_GLOBAL"] = str(gc)
        try:
            self._run_build(full=True)
            amb_hist = [c["files"] for c in iss._collect_git_history(self.root)[1]]
            amb_fresh = iss.freshness_for_paths(
                self.index_dir, ["src/new_name.py", "docs/g.md"])
            amb_row = iss.doc_drift_for_path(self.index_dir, "docs/g.md")
        finally:
            if saved is None:
                os.environ.pop("GIT_CONFIG_GLOBAL", None)
            else:
                os.environ["GIT_CONFIG_GLOBAL"] = saved
        self.assertEqual(amb_hist, clean_hist,
                         "history must match the clean control under GIT_CONFIG_GLOBAL")
        self.assertEqual(amb_fresh, clean_fresh,
                         "freshness must match the clean control under GIT_CONFIG_GLOBAL")
        self.assertEqual(amb_row["commits_since"], clean_row["commits_since"])
        self.assertEqual(amb_row["drifted"], clean_row["drifted"])


class _OrphanStoreCase(_EpochBuildCase):
    """Shared harness for the 1u8o2 (1u8nz) orphan-store fixtures.

    Orphan state = store rows present, registry (build_file_meta) rows absent,
    files gone from disk: the fielded corpus shape after out-of-band cleanup or
    an older pack's bug. Constructed through the canonical producers (a real
    full build) and then poisoned, because no current producer can mint it."""

    _FILES = {
        "src/app.py": "def app():\n    return 1\n",
        "src/payload_mod.py": "def debris():\n    return 42\n",
        "docs/guide.md": "## Guide\n\nKeep me around.\n",
        "docs/debris_note.md": "## Debris\n\nPhantom transition-run note.\n",
    }
    _NEEDLES = ("debris_note", "payload_mod")

    def _seed_and_poison(self):
        _make_repo(self.root, self._FILES)
        self._run_build(full=True)
        meta = _read_meta_store(self.index_dir)
        fm = meta.get("file_meta") or {}
        for k in list(fm):
            if any(n in k for n in self._NEEDLES):
                del fm[k]
        meta["file_meta"] = fm
        _seed_meta_store(self.index_dir, meta)
        (self.root / "docs" / "debris_note.md").unlink()
        (self.root / "src" / "payload_mod.py").unlink()

    def _sqlite_paths(self, db_file: Path, table: str) -> set[str]:
        # Wave 1xny6: every one of these tables lives in the SHARED index
        # database, which may only be opened through sqlite_runtime.
        import index_state_store
        import sqlite_runtime

        if not db_file.exists():
            return set()
        conn = sqlite_runtime.connect(db_file, read_only=True)
        try:
            return {str(r[0]) for r in conn.execute(f"SELECT DISTINCT path FROM {table}")}
        finally:
            conn.close()

    def _state_db(self) -> Path:
        import index_state_store

        return index_state_store.state_store_path(self.index_dir)

    def _graph_db(self) -> Path:
        # The graph extraction manifest is a table in the shared database now.
        return self._state_db()

    def _store_needle_map(self) -> dict[str, set[str]]:
        return {
            "file_freshness": self._sqlite_paths(self._state_db(), "file_freshness"),
            "secret_scan_cache": self._sqlite_paths(self._state_db(), "secret_scan_cache"),
            "graph_files": self._sqlite_paths(self._graph_db(), "graph_file_state"),
        }

    def _needles_in(self, paths: set[str]) -> list[str]:
        return sorted(p for p in paths if any(n in p for n in self._NEEDLES))


class OrphanStoreReconcileTests(_OrphanStoreCase):
    """Wave 1u8o2 (1u8nz) AC-1/AC-4: one incremental build reconciles orphaned
    graph and sidecar rows, inside the build epoch, driving the real stores.
    Red-first: pre-fix, the zero-change incremental left all three stores
    holding the orphans (probe-proven; see the change doc's Progress Log)."""

    def test_one_incremental_reconciles_graph_and_sidecar_orphans(self):
        # AC-1: red against pre-fix code (orphans survive), green post-fix.
        self._seed_and_poison()
        before = self._store_needle_map()
        for store, paths in before.items():
            self.assertTrue(
                self._needles_in(paths),
                f"precondition: poisoned fixture must hold orphans in {store}",
            )
        result = self._run_build(full=False)
        self.assertNotIn("error", result, result.get("error", ""))
        after = self._store_needle_map()
        for store, paths in after.items():
            self.assertEqual(
                self._needles_in(paths), [],
                f"one incremental must reconcile orphaned rows out of {store}",
            )
        # Pin: the Lance/registry self-heal path stays intact alongside.
        docs = {row["path"] for row in _read_index_chunks(self.index_dir, "docs")}
        code = {row["path"] for row in _read_index_chunks(self.index_dir, "code")}
        self.assertEqual(self._needles_in(docs | code), [])
        # Surviving corpus is untouched.
        self.assertIn("docs/guide.md", after["file_freshness"])
        self.assertIn("src/app.py", after["graph_files"])

    def test_build_path_with_real_change_reconciles_sidecar_orphan(self):
        # Delivery-review repair (QA P2-1): pin the BUILD-path reap seam
        # wiring (indexer.py, the reconcile after the Lance reap), not just
        # the zero-change idle pass. A genuine file change forces build_index
        # down the changed/build path, where the idle-pass reconcile never
        # runs; only the build-path seam can reap the sidecar orphan. Kills
        # the mutant that disables the build-path invocation (`if any(...)`
        # replaced with `if False`), which no prior test caught.
        import sqlite3
        _make_repo(self.root, {
            "src/app.py": self._FILES["src/app.py"],
            "docs/guide.md": self._FILES["docs/guide.md"],
        })
        self._run_build(full=True)
        # Sidecar orphan: a secret_scan_cache row whose path is absent from
        # BOTH the registry and disk (inserted directly; older-pack residue
        # is unreachable through current producers by definition).
        conn = sqlite3.connect(str(self._state_db()))
        try:
            with conn:
                conn.execute(
                    "INSERT OR REPLACE INTO secret_scan_cache "
                    "(path, content_hash, rules_fingerprint, scanned_at, clean, finding_refs) "
                    "VALUES ('docs/phantom_note.md', 'x', 'y', 0, 1, '[]')"
                )
        finally:
            conn.close()
        # GENUINE change: the incremental must take the changed/build path.
        (self.root / "docs" / "guide.md").write_text(
            "## Guide\n\nKeep me around. Edited for the build path.\n",
            encoding="utf-8",
        )
        result = self._run_build(full=False)
        self.assertNotIn("error", result, result.get("error", ""))
        self.assertIsNot(
            result.get("up_to_date"), True,
            "precondition: the build must take the changed path, not the idle pass",
        )
        self.assertNotIn(
            "docs/phantom_note.md",
            self._sqlite_paths(self._state_db(), "secret_scan_cache"),
            "one changed-path build must reap the sidecar orphan at the "
            "build-path reconcile seam",
        )
        # Surviving corpus is untouched.
        self.assertIn(
            "docs/guide.md", self._sqlite_paths(self._state_db(), "file_freshness"))

    def test_removal_only_pass_opens_and_finalizes_epoch(self):
        # AC-4: a reconcile with ONLY sidecar orphan work (Lance already clean)
        # opens and finalizes a build epoch: the generation advances and the
        # published state is complete.
        import sqlite3
        _make_repo(self.root, {
            "src/app.py": self._FILES["src/app.py"],
            "docs/guide.md": self._FILES["docs/guide.md"],
        })
        self._run_build(full=True)
        # Sidecar-only orphans, inserted directly: this state is unreachable
        # through current producers by definition (it is older-pack residue),
        # and inserting only sidecar rows keeps Lance/registry/graph clean so
        # the reconcile is the ONLY work in the pass.
        conn = sqlite3.connect(str(self._state_db()))
        try:
            with conn:
                conn.execute(
                    "INSERT OR REPLACE INTO file_freshness "
                    "(path, last_modified, churn_score, commit_count, source, updated_at) "
                    "VALUES ('docs/phantom_note.md', 0, 0.0, 0, 'git', 0)"
                )
                conn.execute(
                    "INSERT OR REPLACE INTO secret_scan_cache "
                    "(path, content_hash, rules_fingerprint, scanned_at, clean, finding_refs) "
                    "VALUES ('docs/phantom_note.md', 'x', 'y', 0, 1, '[]')"
                )
        finally:
            conn.close()
        gen_before = self._generation()
        result = self._run_build(full=False)
        self.assertIs(result.get("up_to_date"), True)
        self.assertGreater(
            self._generation(), gen_before,
            "a removal-only reconcile pass must open and finalize a build epoch",
        )
        state = self.iss.read_build_state(self.index_dir)
        self.assertEqual((state or {}).get("status"), "complete")
        self.assertNotIn(
            "docs/phantom_note.md",
            self._sqlite_paths(self._state_db(), "file_freshness"),
        )
        self.assertNotIn(
            "docs/phantom_note.md",
            self._sqlite_paths(self._state_db(), "secret_scan_cache"),
        )
        # And the pass converges: the NEXT build is a true no-op (no epoch churn).
        gen_after = self._generation()
        self._run_build(full=False)
        self.assertEqual(self._generation(), gen_after,
                         "a clean follow-up build must not reopen the epoch")


class LanceSelfHealOrderingPinTests(_OrphanStoreCase):
    """Wave 1u8o2 (1u8nz) AC-2: the four healing orderings verified by the
    prepare-cycle probes stay green: Lance/FTS/registry self-heal and
    scope-departure retirement are pinned, not modified."""

    _IGNORE_RULES = "debris_note.md\npayload_mod.py\n"

    def _needle_state(self):
        meta = set((_read_meta_store(self.index_dir).get("file_meta") or {}).keys())
        docs = {row["path"] for row in _read_index_chunks(self.index_dir, "docs")}
        code = {row["path"] for row in _read_index_chunks(self.index_dir, "code")}
        return meta, docs, code

    def _assert_needles_gone(self, label: str):
        meta, docs, code = self._needle_state()
        self.assertEqual(self._needles_in(meta), [], f"{label}: meta")
        self.assertEqual(self._needles_in(docs), [], f"{label}: docs table")
        self.assertEqual(self._needles_in(code), [], f"{label}: code table")

    def _seed(self):
        _make_repo(self.root, self._FILES)
        self._run_build(full=True)

    def test_ordering_ignore_and_delete_then_update(self):
        # Field ordering: ignore + delete with no build between, then update.
        self._seed()
        (self.root / ".gitignore").write_text(self._IGNORE_RULES, encoding="utf-8")
        (self.root / "docs" / "debris_note.md").unlink()
        (self.root / "src" / "payload_mod.py").unlink()
        self._run_build(full=False)
        self._assert_needles_gone("ignore+delete+update")

    def test_ordering_long_with_intermediate_build(self):
        # Long ordering: ignore, build, delete, build.
        self._seed()
        (self.root / ".gitignore").write_text(self._IGNORE_RULES, encoding="utf-8")
        self._run_build(full=False)
        (self.root / "docs" / "debris_note.md").unlink()
        (self.root / "src" / "payload_mod.py").unlink()
        self._run_build(full=False)
        self._assert_needles_gone("ignore, build, delete, build")

    def test_ordering_scoped_docs_then_code_updates(self):
        # Scoped ordering: docs-only then code-only updates after ignore+delete.
        self._seed()
        (self.root / ".gitignore").write_text(self._IGNORE_RULES, encoding="utf-8")
        (self.root / "docs" / "debris_note.md").unlink()
        (self.root / "src" / "payload_mod.py").unlink()
        self._run_build(full=False, content="docs")
        self._run_build(full=False, content="code")
        self._assert_needles_gone("scoped docs-only then code-only updates")

    def test_ordering_ignored_but_present_retires(self):
        # Ignored-but-present: scope departure retires rows while files stay on
        # disk (shipped Lance behavior; the graph aligns to it per the parity
        # decision in the change doc).
        self._seed()
        (self.root / ".gitignore").write_text(self._IGNORE_RULES, encoding="utf-8")
        self._run_build(full=False)
        _meta, docs, code = self._needle_state()
        self.assertEqual(self._needles_in(docs), [], "ignored-but-present: docs table")
        self.assertEqual(self._needles_in(code), [], "ignored-but-present: code table")


class OrphanReconcilePlanUnitTests(_OrphanStoreCase):
    """Wave 1u8o2 (1u8nz) AC-3 + AC-6: absence classification via error
    injection at the stat seam (never chmod), the mass-removal circuit
    breaker, and the structural perf properties (one stat per unique
    candidate; no directory traversal)."""

    def _authority(self) -> set[str]:
        return set((_read_meta_store(self.index_dir).get("file_meta") or {}).keys())

    def test_enoent_removes_unreadable_preserves(self):
        # AC-3: ENOENT (debris paths, really deleted) plans removal; an
        # injected EACCES at the stat seam preserves the row in every store.
        self._seed_and_poison()
        real_stat = os.stat

        def inject(path):
            if "payload_mod" in str(path):
                raise PermissionError(13, "injected EACCES", str(path))
            return real_stat(path)

        with patch.object(self.bi, "_orphan_path_stat", side_effect=inject):
            plan = self.bi._plan_orphan_store_reconcile(
                self.root, self.index_dir, self._authority()
            )
        for store in ("file_freshness", "secret_scan_cache", "graph"):
            self.assertFalse(
                any("payload_mod" in p for p in plan[store]),
                f"unreadable path must be preserved in {store}",
            )
        for store in ("file_freshness", "secret_scan_cache", "graph"):
            self.assertTrue(
                any("debris_note" in p for p in plan[store]),
                f"ENOENT path must plan removal in {store}",
            )

    def test_present_but_out_of_scope_parity(self):
        # Decision (recorded in the change doc): freshness and graph rows for
        # present-but-out-of-scope paths retire (parity with the shipped Lance
        # eligibility reap); the secret-scan cache keeps them (its candidate
        # set is all tracked files, wider than the index corpus by design).
        import sqlite3
        _make_repo(self.root, {
            "src/app.py": self._FILES["src/app.py"],
            "docs/guide.md": self._FILES["docs/guide.md"],
        })
        self._run_build(full=True)
        extra = "docs/present_extra.md"
        (self.root / extra).write_text("## Present\n\nStill on disk.\n", encoding="utf-8")
        conn = sqlite3.connect(str(self._state_db()))
        try:
            with conn:
                conn.execute(
                    "INSERT OR REPLACE INTO file_freshness "
                    "(path, last_modified, churn_score, commit_count, source, updated_at) "
                    "VALUES (?, 0, 0.0, 0, 'git', 0)",
                    (extra,),
                )
                conn.execute(
                    "INSERT OR REPLACE INTO secret_scan_cache "
                    "(path, content_hash, rules_fingerprint, scanned_at, clean, finding_refs) "
                    "VALUES (?, 'x', 'y', 0, 1, '[]')",
                    (extra,),
                )
        finally:
            conn.close()
        authority = self._authority() - {extra}
        plan = self.bi._plan_orphan_store_reconcile(self.root, self.index_dir, authority)
        self.assertIn(extra, plan["file_freshness"],
                      "present-but-out-of-scope freshness row must retire (parity)")
        self.assertNotIn(extra, plan["secret_scan_cache"],
                         "present tracked file must keep its secret-scan cache row")

    def test_mass_removal_circuit_breaker_defers_with_log(self):
        # AC-3: a would-remove count over the threshold defers the store's
        # reconciliation with an explicit log line.
        import sqlite3
        _make_repo(self.root, {
            "src/app.py": self._FILES["src/app.py"],
            "docs/guide.md": self._FILES["docs/guide.md"],
        })
        self._run_build(full=True)
        phantoms = [f"docs/phantom_{i}.md" for i in range(9)]
        conn = sqlite3.connect(str(self._state_db()))
        try:
            with conn:
                for p in phantoms:
                    conn.execute(
                        "INSERT OR REPLACE INTO file_freshness "
                        "(path, last_modified, churn_score, commit_count, source, updated_at) "
                        "VALUES (?, 0, 0.0, 0, 'git', 0)",
                        (p,),
                    )
        finally:
            conn.close()
        # Non-vacuity: 9 phantoms over a small store trips BOTH breaker legs
        # (9 >= min-rows floor of 8, and 9 > half the store rows).
        buf = io.StringIO()
        with redirect_stderr(buf):
            plan = self.bi._plan_orphan_store_reconcile(
                self.root, self.index_dir, self._authority()
            )
        self.assertEqual(plan["file_freshness"], set(),
                         "deferred store must plan zero removals")
        self.assertIn("file_freshness", plan["deferred"])
        self.assertEqual(plan["deferred"]["file_freshness"]["would_remove"], 9)
        self.assertIn("orphan reconcile DEFERRED", buf.getvalue())
        self.assertIn("file_freshness", buf.getvalue())

    def test_at_most_one_stat_per_unique_candidate(self):
        # AC-6: the classification cache is shared across stores, so a candidate
        # present in all three stores is statted exactly once, and rows the
        # authority knows are never statted at all.
        self._seed_and_poison()
        calls: list[str] = []
        real_stat = os.stat

        def spy(path):
            calls.append(str(path))
            return real_stat(path)

        with patch.object(self.bi, "_orphan_path_stat", side_effect=spy):
            plan = self.bi._plan_orphan_store_reconcile(
                self.root, self.index_dir, self._authority()
            )
        self.assertEqual(len(calls), len(set(calls)),
                         "each unique candidate is statted at most once")
        authority = self._authority()
        store_paths = _store_mod().orphan_store_paths(self.index_dir)
        expected_candidates = (
            (store_paths["file_freshness"] | store_paths["secret_scan_cache"]
             | store_paths["graph"]) - authority
        )
        self.assertEqual(
            len(calls), len(expected_candidates),
            "exactly the unique out-of-authority candidates are statted (the "
            "needles appear in all three stores yet are statted once each)",
        )
        self.assertEqual(plan["stat_calls"], len(calls))
        for needle in self._NEEDLES:
            self.assertEqual(
                sum(1 for p in calls if needle in p), 1,
                f"cross-store candidate {needle} must be statted exactly once",
            )
        for p in calls:
            rel = str(Path(p).relative_to(self.root)).replace("\\", "/")
            self.assertNotIn(rel, authority,
                             f"in-authority path must never be statted: {rel}")

    def test_reconcile_never_descends_directories(self):
        # AC-6 poisoned-tree spy: plan + sidecar execution never call any
        # directory-iteration primitive, so an ignored tree (or any tree) is
        # never descended (per-row stats only).
        self._seed_and_poison()
        ignored = self.root / "node_modules" / "pkg"
        ignored.mkdir(parents=True)
        (ignored / "index.js").write_text("// ignored\n", encoding="utf-8")
        (self.root / ".gitignore").write_text("node_modules/\n", encoding="utf-8")

        def boom(*_a, **_k):
            raise AssertionError("orphan reconcile must not iterate directories")

        with patch("os.scandir", side_effect=boom), patch("os.walk", side_effect=boom), \
                patch("os.listdir", side_effect=boom):
            plan = self.bi._plan_orphan_store_reconcile(
                self.root, self.index_dir, self._authority()
            )
            plan["graph"] = set()  # sidecar-only execute: the graph merge is
            # shipped machinery exercised end to end elsewhere (AC-1).
            self.bi._execute_orphan_store_reconcile(self.root, self.index_dir, plan)
        self.assertTrue(plan["file_freshness"],
                        "non-vacuity: the poisoned run still planned real work")


class ModelSwapBenchmarkFixtureTests(unittest.TestCase):
    def setUp(self):
        bench_dir = SCRIPTS_ROOT / "benchmarks"
        spec = importlib.util.spec_from_file_location(
            "embed_bench_fixture", bench_dir / "embed_bench.py"
        )
        self.bench = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(self.bench)
        self.bench_dir = bench_dir

    def test_committed_model_swap_result_recomputes_without_inference(self):
        validation = self.bench.validate_model_swap_result()
        self.assertTrue(validation["ok"], validation["errors"])
        self.assertEqual(
            __import__("hashlib").sha256(
                (self.bench_dir / "retrieval_eval.json").read_bytes()
            ).hexdigest(),
            "0278e75e544d3f387ccff50bfaa3b4469d5d097bb16180918924661b4a292b86",
        )

    def test_validator_detects_rank_provenance_and_timing_mutations(self):
        result = json.loads(
            (self.bench_dir / "model_swap_v2_result.json").read_text(
                encoding="utf-8"
            )
        )
        result["provenance"]["s_revision"] = "mutated"
        result["corpora"]["code"]["per_query"][0]["s_raw_rank"] = 999
        result["corpora"]["documents"]["timing_seconds"]["s"] *= 10
        with tempfile.TemporaryDirectory() as tmp:
            mutated = Path(tmp) / "result.json"
            mutated.write_text(json.dumps(result), encoding="utf-8")
            validation = self.bench.validate_model_swap_result(mutated)
        self.assertFalse(validation["ok"])
        self.assertTrue(any("provenance" in error for error in validation["errors"]))
        self.assertTrue(any("timing ratio" in error for error in validation["errors"]))
        self.assertTrue(
            any(
                "recompute" in error or "loses required" in error
                for error in validation["errors"]
            )
        )

    def test_validator_binds_query_and_accepted_answer_fixture_content(self):
        code_input = json.loads(
            (self.bench_dir / "model_swap_code_queries.json").read_text(
                encoding="utf-8"
            )
        )
        code_input["queries"][0]["query"] = "mutated unrelated query"
        code_input["queries"][0]["accepted"] = ["impossible-answer.py"]
        with tempfile.TemporaryDirectory() as tmp:
            mutated = Path(tmp) / "code-queries.json"
            mutated.write_text(json.dumps(code_input), encoding="utf-8")
            validation = self.bench.validate_model_swap_result(code_path=mutated)
        self.assertFalse(validation["ok"])
        self.assertTrue(
            any("query/answer fixture" in error for error in validation["errors"]),
            validation["errors"],
        )
        self.assertTrue(
            any("query text" in error for error in validation["errors"]),
            validation["errors"],
        )


class OrphanRetirementCallerCensusTests(unittest.TestCase):
    """Wave 1u8o2 (1u8nz) AC-4: the no-out-of-epoch-deletion clause. The new
    deletion APIs are reachable only from the build-epoch reap seam, pinned
    by a reference census over the framework scripts (the universal negative
    is census-verified; the recorded census lives in the change doc)."""

    def _script_sources(self) -> dict[str, str]:
        return {
            p.name: p.read_text(encoding="utf-8")
            for p in framework_source_files()
        }

    def test_retire_orphaned_graph_paths_single_production_caller(self):
        sources = self._script_sources()
        referencing = {
            name for name, src in sources.items()
            if "retire_orphaned_graph_paths" in src
        }
        self.assertEqual(
            referencing, {"graph_indexer.py", "indexer.py"},
            "the graph retirement API must have no callers beyond the reap seam",
        )
        indexer_src = sources["indexer.py"]
        self.assertEqual(
            indexer_src.count("retire_orphaned_graph_paths"), 1,
            "indexer.py references the retirement API exactly once (the epoch seam)",
        )
        seam_start = indexer_src.index("def _execute_orphan_store_reconcile")
        seam_end = indexer_src.index("\ndef ", seam_start + 10)
        self.assertIn(
            "retire_orphaned_graph_paths",
            indexer_src[seam_start:seam_end],
            "the single reference lives inside _execute_orphan_store_reconcile",
        )

    def test_remove_sidecar_paths_single_production_caller(self):
        sources = self._script_sources()
        referencing = {
            name for name, src in sources.items()
            if "remove_sidecar_paths" in src
        }
        self.assertEqual(
            referencing, {"index_state_store.py", "indexer.py"},
            "the sidecar deletion API must have no callers beyond the reap seam",
        )


class DocCodeTableRoutingTests(unittest.TestCase):
    """Wave 1wik9 (1whup): doc-code chunks from documentation files route to
    the DOCS table via _is_docs_kind. Before this change every extracted
    fence/directive chunk was kind="code" and the per-table eligibility gate
    (1sek8) dropped it from BOTH tables because docs files are never
    code-eligible."""

    def setUp(self):
        self.bi = load_build_index()

    def test_is_docs_kind_carries_doc_code(self):
        self.assertTrue(self.bi._is_docs_kind("doc-code"))
        self.assertFalse(self.bi._is_docs_kind("code"))

    def test_docs_file_fence_chunks_land_in_the_docs_split(self):
        src = (
            "# Guide\n\n## Install\n\nRun this.\n\n"
            "```bash\nwidgetctl install --profile default\n```\n"
        )
        dc, cc = self.bi._chunks_for_file("docs/guide.md", src)
        fence_rows = [c for c in dc if c["kind"] == "doc-code"]
        self.assertEqual(len(fence_rows), 1)
        self.assertIn("widgetctl install", fence_rows[0]["text"])
        # The code split stays empty: no docs file becomes code-eligible.
        self.assertEqual(cc, [])

    def test_rst_directive_chunks_land_in_the_docs_split(self):
        src = (
            "Guide\n=====\n\nUsage\n-----\n\nProse.\n\n"
            ".. code-block:: python\n\n   configure(retries=3)\n"
        )
        dc, cc = self.bi._chunks_for_file("docs/guide.rst", src)
        self.assertTrue(
            any(c["kind"] == "doc-code" and "configure(retries=3)" in c["text"]
                for c in dc))
        self.assertEqual(cc, [])


class DiagramCorpusMembershipTests(unittest.TestCase):
    """Wave 1wik9 (1whuq): diagram-file corpus membership. Registration is
    CHUNKER-ONLY — the six extensions never join _KNOWN_TEXT_EXTENSIONS
    (that registration bypasses the content sniff, and .dot has a binary
    Word-template namesake the sniff excludes today) — and walk behavior is
    unchanged (no WALKER_VERSION bump for this change)."""

    DIAGRAM_EXTS = (".mmd", ".mermaid", ".puml", ".plantuml", ".dot", ".gv")

    def setUp(self):
        self.bi = load_build_index()

    def test_diagram_extensions_stay_out_of_every_walk_extension_set(self):
        for ext in self.DIAGRAM_EXTS:
            self.assertNotIn(ext, self.bi._KNOWN_TEXT_EXTENSIONS,
                             f"{ext} must not bypass the content sniff")
            self.assertNotIn(ext, self.bi.SOURCE_CODE_EXTENSIONS)
            self.assertNotIn(ext, self.bi.BINARY_EXTENSIONS)
            self.assertNotIn(ext, self.bi._GENERATED_EXCLUDE_EXTENSIONS)

    def test_diagram_chunks_land_in_the_docs_split_in_and_out_of_docs_root(self):
        src = "---\ntitle: Flow\n---\nflowchart LR\n    A[Auth] --> B[Tokens]\n"
        for rel in ("docs/diagrams/flow.mmd", "src/architecture/flow.mmd"):
            dc, cc = self.bi._chunks_for_file(rel, src)
            self.assertTrue(
                any(c["kind"] == "doc-code" and "A[Auth] --> B[Tokens]" in c["text"]
                    for c in dc), rel)
            self.assertEqual(cc, [], rel)

    def test_binary_impostor_dot_stays_walk_excluded(self):
        import tempfile
        ole = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 64
        with tempfile.TemporaryDirectory(prefix="wf-dot-impostor-") as tmp:
            root = Path(tmp)
            (root / "legacy-template.dot").write_bytes(ole)
            (root / "real-graph.dot").write_text(
                "digraph G { a -> b; }\n", encoding="utf-8")
            walked = {
                str(p.relative_to(root)).replace("\\", "/")
                for p in self.bi.walk_repo(root, respect_ignore=True)
            }
        self.assertNotIn("legacy-template.dot", walked,
                         "OLE-header .dot must stay sniff-excluded")
        self.assertIn("real-graph.dot", walked)


class EligibilityReapAbsenceGuardTests(_OrphanStoreCase):
    """Wave 1x54z (1u8o3): the Lance eligibility reap classifies every
    stranded candidate before deleting it (``unreadable`` preserves the rows
    AND the layer hashes; ``absent`` and ``present`` reap exactly as before)
    and carries the ``1u8nz`` mass-removal breaker, at the zero-change
    preflight and at the build-path seam alike. Injection at the seams
    (``os.scandir`` for the walk, ``_orphan_path_stat`` for classification),
    never ``chmod``, which is vacuous under root and flaky across platforms.

    Red-first (recorded in the change doc's Progress Log): on the pre-fix
    tree the first build under a denied directory reaped every row of the
    subtree and dropped its layer hashes, and the recovery build re-embedded
    the subtree from scratch."""

    _FILES = {
        "src/app.py": "def app():\n    return 1\n",
        "docs/guide.md": "## Guide\n\nKeep me around.\n",
        "vault/a.py": "def vault_a():\n    return 1\n",
        "vault/b.py": "def vault_b():\n    return 2\n",
        "vault/notes.md": "## Vault\n\nBehind a permissions incident.\n",
    }
    _VAULT = ("vault/a.py", "vault/b.py", "vault/notes.md")

    def _seed(self):
        _make_repo(self.root, self._FILES)
        self._run_build(full=True)

    def _rows(self, table: str) -> dict[str, set[str]]:
        out: dict[str, set[str]] = {}
        for row in _read_index_chunks(self.index_dir, table):
            out.setdefault(row["path"], set()).add(row["id"])
        return out

    def _vault_state(self) -> dict:
        docs, code = self._rows("docs"), self._rows("code")
        layer_docs = self.iss.layer_hashes(self.index_dir, "docs") or {}
        layer_code = self.iss.layer_hashes(self.index_dir, "code") or {}
        return {
            "rows": {p: (docs.get(p, set()) | code.get(p, set())) for p in self._VAULT},
            "hashes": {p: (layer_docs.get(p), layer_code.get(p)) for p in self._VAULT},
        }

    def _denied_scandir(self, rel_dir: str):
        """Make ``os.walk`` lose ONE directory the way a permissions incident
        does: ``scandir`` on it raises EACCES, everything else passes through."""
        real_scandir = os.scandir
        target = (self.root / rel_dir).resolve()

        def denied(path=".", *args, **kwargs):
            if not isinstance(path, int):
                try:
                    hit = Path(os.fsdecode(path)).resolve() == target
                except (OSError, TypeError, ValueError):
                    hit = False
                if hit:
                    raise PermissionError(13, "injected EACCES", os.fsdecode(path))
            return real_scandir(path, *args, **kwargs)

        return patch("os.scandir", new=denied)

    @staticmethod
    def _eacces_for(needle: str):
        real_stat = os.stat

        def inject(path):
            if needle in str(path).replace("\\", "/"):
                raise PermissionError(13, "injected EACCES", str(path))
            return real_stat(path)

        return inject

    def _notes_repo(self, count: int = 10) -> dict[str, set[str]]:
        files = {"src/app.py": self._FILES["src/app.py"]}
        for i in range(count):
            files[f"docs/note_{i}.md"] = f"## Note {i}\n\nBody of note {i}.\n"
        _make_repo(self.root, files)
        self._run_build(full=True)
        return self._rows("docs")

    def _strand_absent(self, paths: list[str]) -> None:
        # 1p312 technique: the bookkeeping already dropped these paths and the
        # files are gone from disk, so the walk sees no change and the build
        # takes the zero-change seam; only the Lance rows (and layer hashes)
        # remain, which is exactly what the preflight reap must judge.
        meta = _read_meta_store(self.index_dir)
        fm = meta.get("file_meta") or {}
        for p in paths:
            fm.pop(p, None)
            (self.root / p).unlink()
        meta["file_meta"] = fm
        _seed_meta_store(self.index_dir, meta)

    # --- AC-1 / Req 6: the walk case (the collector is load-bearing here) ---

    def test_walk_dropped_subtree_is_preserved_and_recovers_without_reembed(self):
        self._seed()
        before = self._vault_state()
        for p in self._VAULT:
            self.assertTrue(before["rows"][p], f"precondition: {p} has Lance rows")
            self.assertNotEqual(before["hashes"][p], (None, None), f"precondition: {p} has a layer hash")
        err = io.StringIO()
        with self._denied_scandir("vault"), redirect_stderr(err):
            first = self._run_build(full=False)
        self.assertNotIn("error", first, first)
        self.assertEqual(
            self._vault_state(), before,
            "zero-change seam (the denial is the only change, so nothing is stale): "
            "a walk-dropped subtree keeps its rows and layer hashes",
        )
        self.assertIn("unreadable", err.getvalue())
        self.assertIn("vault", err.getvalue())
        preserved = first.get("stranded_reap_preserved") or {}
        self.assertEqual(preserved.get("code"), 2, "the envelope says the reap kept unconfirmed rows (SEC-DEL-1)")
        self.assertGreaterEqual(preserved.get("docs", 0), 1)
        # The omission repeats on the next build; so does the preservation.
        with self._denied_scandir("vault"), redirect_stderr(io.StringIO()):
            second = self._run_build(full=False)
        self.assertNotIn("error", second, second)
        self.assertEqual(self._vault_state(), before)
        # Recovery: readable again. Nothing re-embeds and nothing re-hashes.
        with patch.object(self.bi, "_sha256", wraps=self.bi._sha256) as spy, \
                redirect_stderr(io.StringIO()):
            recovered = self._run_build(full=False)
        self.assertIs(recovered.get("up_to_date"), True, recovered)
        self.assertEqual(recovered.get("files_indexed"), 0)
        self.assertEqual(self._vault_state(), before, "recovery: rows and hashes intact")
        hashed = {str(c.args[0]).replace("\\", "/") for c in spy.call_args_list}
        self.assertFalse(
            any("vault/" in h for h in hashed),
            f"recovery must treat the subtree as unchanged (stat cache), not re-hash it: {hashed}",
        )

    # --- AC-1 as written: EACCES injected at the stat seam, both seams ---

    def test_stat_seam_eacces_preserves_at_the_zero_change_seam_and_recovers(self):
        # The zero-change preflight is the one deletion path that judges rows
        # the walk is silent about (bookkeeping already dropped them). At the
        # build-path seam the incremental write deletes ``removed`` rows before
        # the reap runs, and the only SILENT producer of a removal is the walk
        # omission, which the collector neutralises at change detection (the
        # walk-case test above). So the stat seam is exercised where it judges.
        self._seed()
        before = self._vault_state()
        away = tempfile.TemporaryDirectory()
        self.addCleanup(away.cleanup)
        shutil.move(str(self.root / "vault"), str(Path(away.name) / "vault"))
        meta = _read_meta_store(self.index_dir)
        meta["file_meta"] = {k: v for k, v in (meta.get("file_meta") or {}).items()
                             if not k.startswith("vault/")}
        _seed_meta_store(self.index_dir, meta)
        inject = self._eacces_for("vault/")
        gen = self._generation()
        err = io.StringIO()
        with patch.object(self.bi, "_orphan_path_stat", side_effect=inject), redirect_stderr(err):
            idle = self._run_build(full=False)
        self.assertIs(idle.get("up_to_date"), True, idle)
        self.assertEqual(idle.get("stranded_rows_reaped"), 0)
        self.assertEqual(self._vault_state(), before, "zero-change seam: unreadable preserves rows and hashes")
        self.assertEqual(self._generation(), gen, "nothing to reap: no epoch opened")
        self.assertIn("preserved", err.getvalue())
        self.assertIn("unreadable", err.getvalue())
        # Recovery without the injection: nothing re-embeds.
        shutil.move(str(Path(away.name) / "vault"), str(self.root / "vault"))
        with redirect_stderr(io.StringIO()):
            recovered = self._run_build(full=False)
        self.assertIs(recovered.get("up_to_date"), True, recovered)
        self.assertEqual(recovered.get("files_indexed"), 0)
        self.assertEqual(self._vault_state(), before)

    # --- AC-2: the breaker, both seams, both sides of the threshold ---

    def test_breaker_defers_at_zero_change_preflight_and_execute_never_reaps_refused(self):
        docs_before = self._notes_repo(10)
        gone = [f"docs/note_{i}.md" for i in range(9)]
        table_paths = len(docs_before)
        self.assertGreaterEqual(len(gone), self.bi.ORPHAN_RECONCILE_BREAKER_MIN_ROWS)
        self.assertGreater(len(gone), self.bi.ORPHAN_RECONCILE_BREAKER_FRACTION * table_paths,
                           "non-vacuity: the fixture trips BOTH breaker legs")
        self._strand_absent(gone)
        gen = self._generation()
        err = io.StringIO()
        # The sidecar reconciliation (1u8nz) decides for itself at this seam
        # and, in a non-git fixture, its secret-scan denominator depends on a
        # scan-versus-Lance write race; neutralise it so the epoch assertion
        # below is about the reap alone (the sidecars have their own tests).
        empty_plan = {"file_freshness": set(), "secret_scan_cache": set(), "graph": set(),
                      "deferred": {}, "stat_calls": 0}
        with patch.object(self.bi, "_plan_orphan_store_reconcile", return_value=empty_plan), \
                redirect_stderr(err):
            result = self._run_build(full=False)
        self.assertIs(result.get("up_to_date"), True, result)
        self.assertEqual(result.get("stranded_rows_reaped"), 0)
        self.assertEqual(self._rows("docs"), docs_before, "deferred: not one docs row reaped")
        layer = self.iss.layer_hashes(self.index_dir, "docs") or {}
        for p in gone:
            self.assertIn(p, layer, "deferred: layer hashes untouched")
        self.assertEqual(self._generation(), gen, "a fully deferred preflight opens no epoch")
        self.assertIn("reaper DEFERRED", err.getvalue())
        self.assertIn("docs", err.getvalue())
        self.assertIn("mode='rebuild'", err.getvalue(), "the message names the remedy")
        self.assertEqual(
            result.get("stranded_reap_deferred"), {"docs": {"would_reap": 9, "table_paths": table_paths}},
            "a deferred preflight is reported in the build result, not only on stderr",
        )

    def test_one_stranded_path_under_the_breaker_reaps_at_the_zero_change_seam(self):
        docs_before = self._notes_repo(10)
        self._strand_absent(["docs/note_0.md"])
        with redirect_stderr(io.StringIO()):
            result = self._run_build(full=False)
        self.assertGreater(result.get("stranded_rows_reaped", 0), 0)
        after = self._rows("docs")
        self.assertNotIn("docs/note_0.md", after)
        self.assertEqual(set(after) | {"docs/note_0.md"}, set(docs_before))
        self.assertNotIn("docs/note_0.md", self.iss.layer_hashes(self.index_dir, "docs") or {})

    def test_breaker_defers_at_the_build_path_seam(self):
        # Rows stranded by an earlier build (bookkeeping already dropped them,
        # files gone) plus a real edit elsewhere: the ordinary build path runs
        # and its reap must judge the 9 absent paths the same way.
        docs_before = self._notes_repo(10)
        gone = [f"docs/note_{i}.md" for i in range(9)]
        self._strand_absent(gone)
        (self.root / "src" / "app.py").write_text("def app():\n    return 2\n", encoding="utf-8")
        err = io.StringIO()
        with redirect_stderr(err):
            result = self._run_build(full=False)
        self.assertNotIn("error", result, result)
        self.assertIsNot(result.get("up_to_date"), True, "non-vacuity: this was a build-path run")
        self.assertEqual(result.get("stranded_rows_reaped"), 0)
        self.assertEqual(self._rows("docs"), docs_before, "deferred: not one docs row reaped")
        layer = self.iss.layer_hashes(self.index_dir, "docs") or {}
        for p in gone:
            self.assertIn(p, layer, "deferred: layer hashes untouched at the build-path seam")
        self.assertIn("reaper DEFERRED", err.getvalue())
        self.assertEqual(result.get("stranded_reap_deferred", {}).get("docs", {}).get("would_reap"), 9,
                         "the build-path result carries the deferral too")

    def test_one_stranded_path_under_the_breaker_reaps_at_the_build_path_seam(self):
        self._notes_repo(10)
        self._strand_absent(["docs/note_0.md"])
        (self.root / "src" / "app.py").write_text("def app():\n    return 2\n", encoding="utf-8")
        with redirect_stderr(io.StringIO()):
            result = self._run_build(full=False)
        self.assertIsNot(result.get("up_to_date"), True, "non-vacuity: this was a build-path run")
        self.assertGreater(result.get("stranded_rows_reaped", 0), 0)
        self.assertNotIn("docs/note_0.md", self._rows("docs"))
        self.assertNotIn("docs/note_0.md", self.iss.layer_hashes(self.index_dir, "docs") or {})

    # --- AC-3: the walk surfaces the directory; classification needs no stat ---

    def test_walk_repo_surfaces_the_unreadable_directory(self):
        _make_repo(self.root, self._FILES)
        unreadable: set[str] = set()
        with self._denied_scandir("vault"):
            walked = {
                str(p.relative_to(self.root)).replace("\\", "/")
                for p in self.bi.walk_repo(self.root, respect_ignore=True, unreadable_dirs=unreadable)
            }
        self.assertEqual(unreadable, {"vault"})
        self.assertFalse(any(p.startswith("vault/") for p in walked), walked)
        self.assertIn("src/app.py", walked)
        # The root itself unreadable: "." shadows every path and the walk is empty.
        at_root: set[str] = set()
        with self._denied_scandir("."):
            walked_root = self.bi.walk_repo(self.root, respect_ignore=True, unreadable_dirs=at_root)
        self.assertEqual(walked_root, [])
        self.assertEqual(at_root, {"."})
        # Without a collector the walk is unchanged (every existing caller).
        with self._denied_scandir("vault"):
            plain = self.bi.walk_repo(self.root, respect_ignore=True)
        self.assertEqual({str(p.relative_to(self.root)).replace("\\", "/") for p in plain}, walked)

    def test_candidate_under_a_surfaced_directory_classifies_unreadable_without_stat(self):
        self._seed()
        calls: list[str] = []
        real_stat = os.stat

        def spy(path):
            calls.append(str(path).replace("\\", "/"))
            return real_stat(path)

        with patch.object(self.bi, "_orphan_path_stat", side_effect=spy):
            plan = self.bi._reap_stranded_vector_rows(
                self.index_dir,
                {"src/app.py", "docs/guide.md"},
                root=self.root,
                tables=("docs", "code"),
                plan_only=True,
                unreadable_dirs={"vault"},
            )
        preserved = plan["preserved_by_table"]
        self.assertEqual(preserved["code"], {"vault/a.py", "vault/b.py"})
        self.assertEqual(preserved["docs"], {"vault/notes.md"})
        planned = set().union(*plan["paths_by_table"].values())
        self.assertFalse(any(p.startswith("vault/") for p in planned), planned)
        self.assertFalse(any("vault/" in c for c in calls),
                         f"no per-file stat under a surfaced directory: {calls}")

    # --- AC-4: genuine deletion and scope departure are pinned unchanged ---

    def test_genuine_deletion_and_scope_departure_still_reap_and_drop_hashes(self):
        # Outcome pin, exactly as before this change: on the ordinary build
        # path the incremental write already deletes ``removed`` rows before
        # the reap runs, so the pin is on the result, not on the reap's count.
        self._seed()
        (self.root / "vault" / "a.py").unlink()                                   # absent
        (self.root / ".gitignore").write_text("vault/b.py\n", encoding="utf-8")   # present, out of scope
        with redirect_stderr(io.StringIO()):
            result = self._run_build(full=False)
        self.assertNotIn("error", result, result)
        code = self._rows("code")
        self.assertNotIn("vault/a.py", code, "a genuinely deleted file still reaps")
        self.assertNotIn("vault/b.py", code, "a scope-departed file still reaps")
        layer = self.iss.layer_hashes(self.index_dir, "code") or {}
        self.assertNotIn("vault/a.py", layer)
        self.assertNotIn("vault/b.py", layer)
        self.assertIn("vault/notes.md", self._rows("docs"), "an untouched sibling survives")

    def test_reap_classifies_present_out_of_scope_and_absent_as_reapable(self):
        # The reap's own classification through the real stat seam (no
        # injection): a present path outside the eligible set (the narrowing
        # case the reap exists for) and an absent one both plan for reaping;
        # nothing is preserved or deferred. Delivery review QA-DEL-6 replaced
        # an earlier version whose absent leg asserted nothing.
        self._seed()
        (self.root / "vault" / "a.py").unlink()                                   # absent
        self.assertTrue((self.root / "vault" / "b.py").is_file())                 # present
        eligible = set((_read_meta_store(self.index_dir).get("file_meta") or {}).keys())
        eligible -= {"vault/a.py", "vault/b.py"}
        with redirect_stderr(io.StringIO()):
            plan = self.bi._reap_stranded_vector_rows(
                self.index_dir, eligible, root=self.root, tables=("docs", "code"), plan_only=True,
                eligible_by_table={"docs": eligible, "code": eligible},
            )
        self.assertIn("vault/a.py", plan["paths_by_table"]["code"], "absent reaps")
        self.assertIn("vault/b.py", plan["paths_by_table"]["code"], "present-but-out-of-scope reaps")
        self.assertEqual(plan["preserved_by_table"], {"docs": set(), "code": set()})
        self.assertEqual(plan["deferred_by_table"], {})

    # --- Delivery review round 1 (2026-09-04): the build-path seam and the guards it exposed ---

    def test_walk_dropped_subtree_survives_a_build_path_run(self):
        # CODE-DEL-1/2, QA-DEL-1/2, RED-DEL-1, ARCH-DEL-1: an unrelated edit
        # during the outage takes the ordinary build path, where the
        # incremental Lance write, the layer-hash commit, the bookkeeping
        # write and the graph merge all run. Every store keeps the subtree,
        # and the recovery is a stat-cache hit that re-hashes and re-extracts
        # nothing. Pre-repair the graph lost the subtree here for good.
        self._seed()
        before = self._vault_state()
        graph_before = self._sqlite_paths(self._graph_db(), "graph_file_state")
        self.assertTrue(set(self._VAULT) <= graph_before, graph_before)
        (self.root / "src" / "app.py").write_text("def app():\n    return 2\n", encoding="utf-8")
        err = io.StringIO()
        with self._denied_scandir("vault"), redirect_stderr(err):
            outage = self._run_build(full=False)
        self.assertNotIn("error", outage, outage)
        self.assertIsNot(outage.get("up_to_date"), True, "non-vacuity: the edit made this a build-path run")
        self.assertEqual(self._vault_state(), before, "build-path seam: rows and layer hashes kept")
        preserved = outage.get("stranded_reap_preserved") or {}
        self.assertEqual(preserved.get("code"), 2, "the build-path envelope reports the preserved paths (SEC-DEL-1)")
        bookkeeping = set((_read_meta_store(self.index_dir).get("file_meta") or {}).keys())
        self.assertTrue(set(self._VAULT) <= bookkeeping, "the bookkeeping carried the subtree forward")
        self.assertTrue(
            set(self._VAULT) <= self._sqlite_paths(self._graph_db(), "graph_file_state"),
            "the graph merge kept the shadowed subtree instead of pruning it on walk parity",
        )
        self.assertTrue(set(self._VAULT) <= self._sqlite_paths(self._state_db(), "file_freshness"))
        with patch.object(self.bi, "_sha256", wraps=self.bi._sha256) as spy, \
                redirect_stderr(io.StringIO()):
            recovered = self._run_build(full=False)
        self.assertIs(recovered.get("up_to_date"), True, recovered)
        hashed = {str(c.args[0]).replace("\\", "/") for c in spy.call_args_list}
        self.assertFalse(any("vault/" in h for h in hashed), f"recovery re-hashed the subtree: {hashed}")
        self.assertEqual(self._vault_state(), before)
        self.assertTrue(
            set(self._VAULT) <= self._sqlite_paths(self._graph_db(), "graph_file_state"),
            "recovery: the graph still holds the subtree",
        )

    def test_root_unreadable_is_a_loud_no_op_through_the_real_build(self):
        # CODE-DEL-3: the root rule of the shadow helper, driven end to end.
        self._seed()
        before = self._vault_state()
        keys_before = set((_read_meta_store(self.index_dir).get("file_meta") or {}).keys())
        gen = self._generation()
        err = io.StringIO()
        with self._denied_scandir("."), redirect_stderr(err):
            result = self._run_build(full=False)
        self.assertIs(result.get("up_to_date"), True, result)
        self.assertEqual(result.get("files_total"), 0)
        self.assertEqual(self._vault_state(), before, "nothing reaped under a denied root")
        self.assertEqual(set((_read_meta_store(self.index_dir).get("file_meta") or {}).keys()), keys_before)
        self.assertEqual(self._generation(), gen, "no epoch: a denied root is a loud no-op")
        self.assertIn("unreadable", err.getvalue())

    def test_shadow_prefix_is_a_directory_boundary(self):
        # QA-DEL-4 / CODE-DEL-3: the boundary and the root rule, in both modules.
        f = self.bi._shadowed_by_unreadable
        self.assertTrue(f("vault/a.py", {"vault"}))
        self.assertTrue(f("vault", {"vault"}))
        self.assertTrue(f("vault/deep/x.py", {"vault/"}))
        self.assertFalse(f("vaultx/a.py", {"vault"}), "a sibling directory is not shadowed")
        self.assertFalse(f("src/vault/a.py", {"vault"}), "the prefix anchors at the root")
        self.assertTrue(f("anything/at/all.py", {"."}), "the root shadows every path")
        self.assertFalse(f("vault/a.py", set()))
        self.assertFalse(f("vault/a.py", None))
        g = self.bi._get_graph_indexer()._path_under_unreadable
        self.assertTrue(g("vault/a.py", {"vault"}))
        self.assertFalse(g("vaultx/a.py", {"vault"}))
        self.assertTrue(g("x/y.py", {"."}))
        self.assertFalse(g("vault/a.py", None))

    def test_walk_error_without_a_filename_is_recorded_as_the_root(self):
        # CODE-DEL-3: an unmappable scandir failure is recorded conservatively.
        _make_repo(self.root, self._FILES)
        real_scandir = os.scandir
        target = self.root.resolve()

        def denied(path=".", *args, **kwargs):
            if not isinstance(path, int) and Path(os.fsdecode(path)).resolve() == target:
                raise PermissionError(13, "injected EACCES with no filename")
            return real_scandir(path, *args, **kwargs)

        unreadable: set[str] = set()
        with patch("os.scandir", new=denied):
            walked = self.bi.walk_repo(self.root, respect_ignore=True, unreadable_dirs=unreadable)
        self.assertEqual(walked, [])
        self.assertEqual(unreadable, {"."}, "an unmappable failure is recorded as the root")

    def _absent_plan_case(self, notes: int, gone: int):
        # A fresh repository per case: ``notes`` docs, ``gone`` of them deleted
        # from disk and dropped from the eligible set, then the plan-only reap.
        # Returns (distinct docs paths in the table, the plan).
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        index_dir = root / ".wavefoundry" / "index"
        files = {"src/app.py": self._FILES["src/app.py"]}
        for i in range(notes):
            files[f"docs/note_{i}.md"] = f"## Note {i}\n\nBody of note {i}.\n"
        _make_repo(root, files)
        docs_mock = _make_embedder_mock(dim=4)
        code_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", side_effect=[docs_mock, code_mock]):
            self.bi.build_index(root, full=True, content="all", verbose=False)
        docs_paths = {row["path"] for row in _read_index_chunks(index_dir, "docs")}
        gone_paths = [f"docs/note_{i}.md" for i in range(gone)]
        for p in gone_paths:
            (root / p).unlink()
        eligible = docs_paths - set(gone_paths)
        with redirect_stderr(io.StringIO()):
            plan = self.bi._reap_stranded_vector_rows(
                index_dir, eligible, root=root, tables=("docs",), plan_only=True,
                eligible_by_table={"docs": eligible},
            )
        return len(docs_paths), plan

    def test_breaker_thresholds_are_pinned_on_both_legs(self):
        # QA-DEL-3: Requirement 2's shape, at least MIN_ROWS AND more than
        # FRACTION, pinned at the boundary of each leg with absent candidates.
        min_rows = self.bi.ORPHAN_RECONCILE_BREAKER_MIN_ROWS
        fraction = self.bi.ORPHAN_RECONCILE_BREAKER_FRACTION
        self.assertEqual((min_rows, fraction), (8, 0.5), "the cases below are shaped for the shipped constants")
        # Exactly the floor, over half: defers (8 absent of 14 or 15 docs paths).
        table_paths, plan = self._absent_plan_case(notes=14, gone=8)
        self.assertGreaterEqual(8, min_rows)
        self.assertGreater(8, fraction * table_paths, table_paths)
        self.assertIn("docs", plan["deferred_by_table"], (table_paths, plan))
        self.assertEqual(plan["paths_by_table"]["docs"], set())
        # Over the floor, exactly half: reaps (8 absent of exactly 16 docs paths).
        extra = table_paths - 14  # non-note docs rows the fixture indexes (e.g. the config)
        table_paths, plan = self._absent_plan_case(notes=16 - extra, gone=8)
        self.assertEqual(table_paths, 16, "fixture shape: the fraction leg is judged at exactly half")
        self.assertEqual(plan["deferred_by_table"], {}, "half is not more than half")
        self.assertEqual(len(plan["paths_by_table"]["docs"]), 8)
        # Under the floor, over half: reaps (7 absent of 13 docs paths).
        table_paths, plan = self._absent_plan_case(notes=13 - extra, gone=7)
        self.assertEqual(table_paths, 13)
        self.assertEqual(plan["deferred_by_table"], {}, "seven is under the floor")
        self.assertEqual(len(plan["paths_by_table"]["docs"]), 7)

    def _build_with_tests(self, *, full: bool, include_tests: bool) -> dict:
        docs_mock = _make_embedder_mock(dim=4)
        code_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", side_effect=[docs_mock, code_mock]):
            return self.bi.build_index(
                self.root, full=full, content="all", include_tests=include_tests, verbose=False
            )

    def test_present_scope_departures_reap_whatever_their_count(self):
        # RED-DEL-2: a stat-confirmed scope departure is positive evidence and
        # never counts toward the breaker. At the reap: nine present paths
        # outside the eligible set all plan for reaping. End to end: the
        # include_tests narrowing reaps every test file (the pre-wave
        # behaviour) instead of deferring for ever.
        self._notes_repo(10)
        eligible = set(self._rows("docs")) - {f"docs/note_{i}.md" for i in range(9)}
        with redirect_stderr(io.StringIO()):
            plan = self.bi._reap_stranded_vector_rows(
                self.index_dir, eligible, root=self.root, tables=("docs",), plan_only=True,
                eligible_by_table={"docs": eligible},
            )
        self.assertEqual(plan["deferred_by_table"], {})
        self.assertEqual(plan["preserved_by_table"]["docs"], set())
        self.assertEqual(plan["paths_by_table"]["docs"], {f"docs/note_{i}.md" for i in range(9)})
        # End to end.
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.index_dir = self.root / ".wavefoundry" / "index"
        files = {"src/app.py": self._FILES["src/app.py"], "src/util.py": "def util():\n    return 3\n"}
        for i in range(10):
            files[f"tests/test_t{i}.py"] = f"def test_t{i}():\n    assert True\n"
        _make_repo(self.root, files)
        with redirect_stderr(io.StringIO()):
            self._build_with_tests(full=True, include_tests=True)
        code_before = set(self._rows("code"))
        self.assertEqual(sum(1 for p in code_before if p.startswith("tests/")), 10, code_before)
        err = io.StringIO()
        with redirect_stderr(err):
            result = self._build_with_tests(full=False, include_tests=False)
        self.assertGreater(result.get("stranded_rows_reaped", 0), 0, result)
        self.assertEqual(result.get("stranded_reap_deferred"), {})
        self.assertNotIn("DEFERRED", err.getvalue())
        after = set(self._rows("code"))
        self.assertFalse(any(p.startswith("tests/") for p in after), after)
        layer = self.iss.layer_hashes(self.index_dir, "code") or {}
        self.assertFalse(any(p.startswith("tests/") for p in layer), "layer hashes dropped with the rows")

    def test_orphan_reconcile_treats_shadowed_candidates_as_unreadable(self):
        # RED-DEL-3: the sidecar and graph reconciliation shares the walk
        # report, so the reap and the reconcile apply one policy to the same
        # paths. At the plan: no stat under a surfaced directory and nothing
        # planned for removal. End to end at the zero-change seam: the graph
        # and freshness rows survive alongside the Lance rows.
        self._seed()
        meta = _read_meta_store(self.index_dir)
        meta["file_meta"] = {k: v for k, v in (meta.get("file_meta") or {}).items()
                             if not k.startswith("vault/")}
        _seed_meta_store(self.index_dir, meta)
        authority = set(meta["file_meta"].keys())
        calls: list[str] = []
        real_stat = os.stat

        def spy(path):
            calls.append(str(path).replace("\\", "/"))
            return real_stat(path)

        with patch.object(self.bi, "_orphan_path_stat", side_effect=spy):
            plan = self.bi._plan_orphan_store_reconcile(
                self.root, self.index_dir, authority, unreadable_dirs={"vault"}
            )
        for store in ("file_freshness", "secret_scan_cache", "graph"):
            self.assertFalse(any(p.startswith("vault/") for p in plan[store]), (store, plan[store]))
        self.assertFalse(any("vault/" in c for c in calls), calls)
        graph_before = self._sqlite_paths(self._graph_db(), "graph_file_state")
        self.assertTrue(set(self._VAULT) <= graph_before, graph_before)
        with self._denied_scandir("vault"), redirect_stderr(io.StringIO()):
            result = self._run_build(full=False)
        self.assertIs(result.get("up_to_date"), True, result)
        self.assertEqual(result.get("stranded_rows_reaped"), 0)
        self.assertEqual(result.get("orphan_rows_reconciled", {}).get("graph"), 0)
        self.assertEqual(self._sqlite_paths(self._graph_db(), "graph_file_state"), graph_before)
        self.assertTrue(set(self._VAULT) <= self._sqlite_paths(self._state_db(), "file_freshness"))

    def test_retirement_seam_keeps_the_shadowed_subtree(self):
        # ARCH-RV1-1 / QA-RV1-1 / CODE-RV1-1: real residue (a path the graph
        # store still knows whose file AND bookkeeping entry are gone) gives
        # the graph reconcile a removable orphan, so retire_orphaned_graph_paths
        # actually runs at the zero-change seam while vault/ is shadowed. The
        # retirement must receive the walk report: the residue goes, the
        # subtree stays, and recovery re-extracts nothing.
        files = dict(self._FILES)
        files["stale/gone.py"] = "def gone():\n    return 0\n"
        _make_repo(self.root, files)
        self._run_build(full=True)
        graph_before = self._sqlite_paths(self._graph_db(), "graph_file_state")
        self.assertIn("stale/gone.py", graph_before)
        self.assertTrue(set(self._VAULT) <= graph_before, graph_before)
        self._strand_absent(["stale/gone.py"])
        with self._denied_scandir("vault"), redirect_stderr(io.StringIO()):
            result = self._run_build(full=False)
        self.assertNotIn("error", result, result)
        self.assertIs(result.get("up_to_date"), True, result)
        retired = (result.get("orphan_rows_reconciled") or {}).get("graph")
        self.assertGreaterEqual(retired or 0, 1, "non-vacuity: the retirement ran")
        graph_after = self._sqlite_paths(self._graph_db(), "graph_file_state")
        self.assertNotIn("stale/gone.py", graph_after, "the residue was retired")
        self.assertTrue(
            set(self._VAULT) <= graph_after,
            "retirement seam: the merge kept the shadowed subtree",
        )
        with patch.object(self.bi, "_sha256", wraps=self.bi._sha256) as mock_hash:
            recovery = self._run_build(full=False)
        self.assertIs(recovery.get("up_to_date"), True, recovery)
        self.assertFalse(
            any("vault" in str(c.args[0]) for c in mock_hash.call_args_list),
            "recovery is a stat-cache hit for the preserved subtree",
        )
        self.assertTrue(set(self._VAULT) <= self._sqlite_paths(self._graph_db(), "graph_file_state"))

    def test_full_rebuild_during_outage_refuses_destructive_publication(self):
        # Unified publication refuses implicit full-rebuild removals whose
        # source is unreadable. Graph preparation may already have run, but
        # verified rollback may restore the intact historical snapshot.
        self._seed()
        self.assertTrue(set(self._VAULT) <= self._sqlite_paths(self._graph_db(), "graph_file_state"))
        chunks_before = set(self._rows("code")) | set(self._rows("docs"))
        with self._denied_scandir("vault"), redirect_stderr(io.StringIO()):
            result = self._run_build(full=True)
        self.assertTrue(result.get("failed"), result)
        self.assertIn("unreadable", result["failure"])
        self.assertIsNotNone(self.iss.build_epoch_token(self.index_dir))
        self.assertEqual(set(self._rows("code")) | set(self._rows("docs")), chunks_before)
        recovery = self._run_build(full=True)
        self.assertFalse(recovery.get("failed"), recovery)
        self.assertIsNotNone(self.iss.build_epoch_token(self.index_dir))
        self.assertTrue(set(self._VAULT) <= self._sqlite_paths(self._graph_db(), "graph_file_state"))
        chunks_after = set(self._rows("code")) | set(self._rows("docs"))
        self.assertTrue(set(self._VAULT) <= chunks_after, chunks_after)

    def _edges_from_guide_into_vault(self) -> set[tuple[str, str]]:
        payload = _published_graph_payload(self.bi, self.root)
        return {
            (str(e.get("relation")), str(e.get("target")))
            for e in payload.get("edges", [])
            if "docs/guide.md" in str(e.get("source")) and "vault/" in str(e.get("target"))
        }

    def test_doc_edited_during_outage_keeps_its_link_edges_into_the_subtree(self):
        # RED-RV1-1: a doc re-extracted while vault/ is unreadable resolves its
        # links against the session's current-path set; that set must carry
        # the shadowed known paths or the doc_references_doc edge into the
        # subtree (the link to vault/notes.md) drops silently and, because
        # recovery is a stat-cache hit, stays gone until the doc is edited
        # again. The doc_references_code edge to vault/a.py resolves through
        # the symbol matcher and survives either way; the set equality pins
        # both relations by name.
        files = dict(self._FILES)
        files["docs/guide.md"] = "## Guide\n\nSee [the vault](../vault/notes.md) and `vault/a.py`.\n"
        _make_repo(self.root, files)
        with redirect_stderr(io.StringIO()):
            self._run_build(full=True)
        before = self._edges_from_guide_into_vault()
        self.assertIn(("doc_references_doc", "vault/notes.md"), before)
        self.assertIn(("doc_references_code", "vault/a.py"), before)
        (self.root / "docs" / "guide.md").write_text(
            "## Guide\n\nEdited. See [the vault](../vault/notes.md) and `vault/a.py`.\n",
            encoding="utf-8",
        )
        with self._denied_scandir("vault"), redirect_stderr(io.StringIO()):
            outage = self._run_build(full=False)
        self.assertNotIn("error", outage, outage)
        self.assertIsNot(outage.get("up_to_date"), True, "the edit drives the build path")
        self.assertEqual(
            self._edges_from_guide_into_vault(), before,
            "the edited doc keeps both edges into the shadowed subtree",
        )
        recovery = self._run_build(full=False)
        self.assertIs(recovery.get("up_to_date"), True, recovery)
        self.assertEqual(self._edges_from_guide_into_vault(), before)

    def _mode_000_children(self, rel_dir: str):
        """Model a mode-000 directory faithfully: ``scandir`` on it fails (the
        walk loses it) AND ``stat`` on any child fails with EACCES, which is
        what ``Path.exists`` / ``Path.stat`` see under a real permission
        outage (``Path.exists`` re-raises EACCES rather than returning False)."""
        real_stat = os.stat
        needle = rel_dir.rstrip("/") + "/"

        def denied_stat(path, *args, **kwargs):
            if not isinstance(path, int) and needle in os.fsdecode(path).replace("\\", "/"):
                raise PermissionError(13, "injected EACCES", os.fsdecode(path))
            return real_stat(path, *args, **kwargs)

        return patch("os.stat", new=denied_stat)

    def test_symbol_rename_during_outage_leaves_the_shadowed_doc_untouched(self):
        # ARCH-RV2-1: a shadowed doc whose cached mentions intersect a changed
        # code symbol used to be re-scanned from disk by the merge's
        # impacted-docs pass; under a real outage that stat raises and every
        # build fails until recovery. The pass must skip shadowed records and
        # keep their stored artifacts.
        files = dict(self._FILES)
        files["src/app.py"] = "def frobnicate_widget():\n    return 1\n"
        files["vault/notes.md"] = "## Vault\n\nUses `frobnicate_widget` from the app.\n"
        _make_repo(self.root, files)
        with redirect_stderr(io.StringIO()):
            self._run_build(full=True)
        graph_before = self._sqlite_paths(self._graph_db(), "graph_file_state")
        self.assertTrue(set(self._VAULT) <= graph_before, graph_before)
        rows_before = self._vault_state()
        (self.root / "src" / "app.py").write_text(
            "def frobnicate_widget_v2():\n    return 1\n", encoding="utf-8"
        )
        with self._denied_scandir("vault"), self._mode_000_children("vault"), \
                redirect_stderr(io.StringIO()):
            result = self._run_build(full=False)
        self.assertNotIn("error", result, result)
        self.assertIsNot(result.get("up_to_date"), True, "the rename drives the build path")
        self.assertEqual(result.get("stranded_reap_preserved"), {"docs": 1, "code": 2}, result)
        self.assertTrue(set(self._VAULT) <= self._sqlite_paths(self._graph_db(), "graph_file_state"))
        self.assertEqual(self._vault_state(), rows_before, "the outage build touched nothing under vault")
        recovery = self._run_build(full=False)
        self.assertNotIn("error", recovery, recovery)
        self.assertTrue(set(self._VAULT) <= self._sqlite_paths(self._graph_db(), "graph_file_state"))
        self.assertEqual(self._vault_state(), rows_before)

    # --- Wave 1x6ti (1x551): the reap's deferral / preservation record ---

    def _defer_zero_change(self) -> tuple[dict, int, int]:
        """A zero-change build whose reap defers (the 1x54z breaker fixture);
        returns (result, pre-build generation, table_paths)."""
        docs_before = self._notes_repo(10)
        gone = [f"docs/note_{i}.md" for i in range(9)]
        self._strand_absent(gone)
        gen = self._generation()
        empty_plan = {"file_freshness": set(), "secret_scan_cache": set(), "graph": set(),
                      "deferred": {}, "stat_calls": 0}
        with patch.object(self.bi, "_plan_orphan_store_reconcile", return_value=empty_plan), \
                redirect_stderr(io.StringIO()):
            result = self._run_build(full=False)
        self.assertEqual(
            result.get("stranded_reap_deferred"), {"docs": {"would_reap": 9, "table_paths": len(docs_before)}},
            "non-vacuity: the fixture must defer",
        )
        return result, gen, len(docs_before)

    def _reap_record(self):
        return self.iss.reap_state_for_index(self.index_dir)

    def _raw_reap_meta(self):
        """The raw meta value: the record must be REMOVED when neither map
        applies, not left as an empty placeholder the reader happens to hide."""
        store = self.iss.IndexStateStore(self.index_dir, read_only=True)
        try:
            return store.get_meta(self.iss.META_REAP_STATE)
        finally:
            store.close()

    def test_deferred_zero_change_build_records_the_reap_state(self):
        # AC-1 (red first): before the writer existed no record was written.
        _, gen, table_paths = self._defer_zero_change()
        rec = self._reap_record()
        self.assertIsNotNone(rec, "a deferred zero-change build must leave a record in the store")
        self.assertEqual(rec["deferred"], {"docs": {"would_reap": 9, "table_paths": table_paths}})
        self.assertEqual(rec["preserved"], {})
        self.assertEqual(rec["recorded_generation"], gen,
                         "a deferral opens no epoch, so the stamp is the last completed build's generation")
        self.assertIsInstance(rec["recorded_at"], (int, float))
        self.assertGreater(rec["recorded_at"], 0)

    def test_deferred_idle_maintenance_pass_records_the_reap_state_after_its_finalize(self):
        # AC-1, the third summary-carrying return: a dirty epoch (a builder
        # that died between fence and finalize) sends the zero-change build
        # through idle maintenance, which opens and finalizes its own epoch;
        # the record is written AFTER that finalize, so its stamp is the
        # generation the idle pass published, one ahead of the pre-build one.
        docs_before = self._notes_repo(10)
        gone = [f"docs/note_{i}.md" for i in range(9)]
        self._strand_absent(gone)
        gen_before = self._generation()
        self.iss.begin_build_epoch(self.index_dir, "all")  # leave the epoch `building`
        empty_plan = {"file_freshness": set(), "secret_scan_cache": set(), "graph": set(),
                      "deferred": {}, "stat_calls": 0}
        with patch.object(self.bi, "_plan_orphan_store_reconcile", return_value=empty_plan), \
                redirect_stderr(io.StringIO()):
            result = self._run_build(full=False)
        self.assertIs(result.get("up_to_date"), True, result)
        self.assertEqual(
            result.get("stranded_reap_deferred"), {"docs": {"would_reap": 9, "table_paths": len(docs_before)}},
            "non-vacuity: the idle pass still defers",
        )
        self.assertEqual(self._generation(), gen_before + 1, "non-vacuity: the idle pass published an epoch")
        rec = self._reap_record()
        self.assertIsNotNone(rec, "the idle-maintenance return must leave a record")
        self.assertEqual(rec["deferred"], {"docs": {"would_reap": 9, "table_paths": len(docs_before)}})
        self.assertEqual(rec["recorded_generation"], gen_before + 1,
                         "the idle-maintenance stamp is the generation its finalize published")

    def test_reap_state_record_clears_on_the_next_clean_build(self):
        # AC-1: restoring the stranded files makes the next build an ordinary
        # build-path run where nothing is stranded, so the record is removed.
        self._defer_zero_change()
        self.assertIsNotNone(self._reap_record())
        for i in range(9):
            (self.root / "docs" / f"note_{i}.md").write_text(f"## Note {i}\n\nBody of note {i}.\n", encoding="utf-8")
        with redirect_stderr(io.StringIO()):
            result = self._run_build(full=False)
        self.assertEqual(result.get("stranded_reap_deferred"), {}, result)
        self.assertEqual(result.get("stranded_reap_preserved"), {}, result)
        self.assertIsNone(self._reap_record(), "a build that defers and preserves nothing removes the record")
        self.assertIsNone(self._raw_reap_meta(), "the meta key itself is removed, not blanked")

    def test_full_rebuild_clears_the_reap_state_record(self):
        # AC-1: both reap seams sit behind `not full`; a full rebuild defers and
        # preserves nothing and the diagnostic's own remedy is the rebuild.
        self._defer_zero_change()
        self.assertIsNotNone(self._reap_record())
        with redirect_stderr(io.StringIO()):
            result = self._run_build(full=True)
        self.assertNotIn("error", result, result)
        self.assertIsNone(self._reap_record(), "a full rebuild removes the record")
        self.assertIsNone(self._raw_reap_meta(), "the meta key itself is removed, not blanked")

    def test_dry_run_leaves_the_reap_state_record_untouched(self):
        # AC-1: a dry run reaches the zero-change preflight unlocked (plan
        # 1x81w); the writer skips it, so the record is byte-identical after.
        self._defer_zero_change()
        before = self._reap_record()
        self.assertIsNotNone(before)
        empty_plan = {"file_freshness": set(), "secret_scan_cache": set(), "graph": set(),
                      "deferred": {}, "stat_calls": 0}
        docs_mock = _make_embedder_mock(dim=4)
        code_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", side_effect=[docs_mock, code_mock]), \
                patch.object(self.bi, "_plan_orphan_store_reconcile", return_value=empty_plan), \
                redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            self.bi.build_index(self.root, full=False, content="all", verbose=False, dry_run=True)
        self.assertEqual(self._reap_record(), before, "a dry run must not touch the record")

    def test_shadowed_build_path_run_records_preserved_counts_stamped_with_the_published_generation(self):
        # AC-2: the build-path write lands after the epoch finalize, so the
        # stamp is the generation that published the preserved rows; the
        # recovery build preserves nothing and removes the record.
        self._seed()
        (self.root / "src" / "app.py").write_text("def app():\n    return 2\n", encoding="utf-8")
        with self._denied_scandir("vault"), redirect_stderr(io.StringIO()):
            outage = self._run_build(full=False)
        self.assertNotIn("error", outage, outage)
        preserved = outage.get("stranded_reap_preserved") or {}
        self.assertEqual(preserved.get("code"), 2, "non-vacuity: the build-path run preserved the subtree")
        rec = self._reap_record()
        self.assertIsNotNone(rec, "a preserving build-path run must leave a record")
        self.assertEqual(rec["preserved"], preserved)
        self.assertEqual(rec["deferred"], {})
        self.assertEqual(rec["recorded_generation"], self._generation(),
                         "the build-path stamp is the generation the finalize published")
        with redirect_stderr(io.StringIO()):
            recovered = self._run_build(full=False)
        self.assertIs(recovered.get("up_to_date"), True, recovered)
        self.assertIsNone(self._reap_record(), "recovery preserves nothing and removes the record")
        self.assertIsNone(self._raw_reap_meta(), "the meta key itself is removed, not blanked")

    def test_reap_state_write_failure_never_fails_the_build(self):
        # AC-5: the indexer holds its own store module object, so the patch
        # target is the class the writer instantiates.
        import sqlite3 as _sqlite3
        docs_before = self._notes_repo(10)
        gone = [f"docs/note_{i}.md" for i in range(9)]
        self._strand_absent(gone)
        empty_plan = {"file_freshness": set(), "secret_scan_cache": set(), "graph": set(),
                      "deferred": {}, "stat_calls": 0}
        store_cls = self.bi._get_index_state_store().IndexStateStore

        def boom(self_store, updates):
            raise _sqlite3.OperationalError("database is locked (injected)")

        with patch.object(store_cls, "set_meta", new=boom), \
                patch.object(self.bi, "_plan_orphan_store_reconcile", return_value=empty_plan), \
                redirect_stderr(io.StringIO()):
            result = self._run_build(full=False)
        self.assertNotIn("error", result, "a visibility aid must never fail the build")
        self.assertIs(result.get("up_to_date"), True, result)
        self.assertEqual(
            result.get("stranded_reap_deferred"), {"docs": {"would_reap": 9, "table_paths": len(docs_before)}},
            "the build result still carries the summaries",
        )
        self.assertIsNone(self._reap_record(), "nothing was written")
        log_text = self.iss.store_log_path(self.index_dir).read_text(encoding="utf-8")
        self.assertIn("reap state", log_text)
        self.assertIn("injected", log_text, "the store log names the failure")




class TargetedPublicationContractTests(unittest.TestCase):
    """Native shared SQLite, bounded fake embeddings, no model downloads."""

    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.index_dir = self.root / '.wavefoundry' / 'index'
        self.calls = []
        self.addCleanup(patch.stopall)
        patch.object(self.bi, '_get_embedder', side_effect=lambda *a, **k:
                     _make_embedder_mock(calls=self.calls)).start()
        for name in ('one', 'two'):
            (self.root / f'{name}.py').write_text(
                f'def {name}():\n    """Documentation for {name}."""\n    return 1\n')
        self.assertFalse(self.bi.build_index(self.root, full=True, content='all').get('failed'))
        self.iss = self.bi._get_index_state_store()
        self.gi = self.bi._get_graph_indexer()

    def _rows(self, rel):
        conn = self.iss.open_read_only(self.index_dir)
        try:
            result = {}
            for table, column in (
                ('chunks_docs', 'path'), ('chunks_code', 'path'),
                ('graph_nodes', 'source_file'), ('graph_edges', 'source_file'),
                ('graph_file_state', 'path'), ('graph_merge_state', 'path'),
                ('build_file_meta', 'path'), ('layer_path_state', 'path'),
                ('file_freshness', 'path'), ('secret_scan_cache', 'path')):
                result[table] = conn.execute(f'SELECT * FROM {table} WHERE {column}=?', (rel,)).fetchall()
            for layer in ('docs', 'code'):
                result['vectors_' + layer] = conn.execute(
                    f'SELECT v.* FROM vectors_{layer} v JOIN chunks_{layer} c ON c.id=v.chunk_id WHERE c.path=?', (rel,)).fetchall()
            # FTS text is a participant, not merely a count of canonical rows.
            for table, in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('fts_docs','fts_code') "):
                columns = {r[1] for r in conn.execute(f'PRAGMA table_info({table})')}
                if 'path' in columns:
                    result[table] = conn.execute(f'SELECT * FROM {table} WHERE path=?', (rel,)).fetchall()
            return result
        finally:
            conn.close()

    def _generation(self):
        return self.iss.read_build_state(self.index_dir)['generation']

    def _change_one(self):
        (self.root / 'one.py').write_text('def one():\n    """Changed documentation."""\n    return 12345\n')

    def test_targeted_update_preserves_all_unselected_participants(self):
        before = self._rows('two.py')
        for key in ('chunks_docs', 'chunks_code', 'vectors_docs', 'vectors_code',
                    'fts_docs', 'fts_code', 'graph_nodes', 'graph_file_state', 'build_file_meta', 'layer_path_state'):
            self.assertTrue(before[key], key)
        generation = self._generation()
        (self.root / 'two.py').unlink()  # omission must preserve even an absent source
        self._change_one()
        result = self.bi.build_index(self.root, files=[self.root / 'one.py'], content='all')
        self.assertFalse(result.get('failed'), result)
        self.assertEqual(before, self._rows('two.py'))
        self.assertEqual(generation + 1, self._generation())
        self.assertEqual(self.bi._sha256(self.root / 'one.py'),
                         _read_meta_store(self.index_dir)['file_meta']['one.py']['hash'])

    def test_targeted_empty_and_explicit_delete_then_complete_walk(self):
        before = self._rows('two.py')
        self._change_one()
        self.assertFalse(self.bi.build_index(self.root, files=[self.root / 'one.py'], content='all').get('failed'))
        self.calls.clear()
        generation = self._generation()
        self.assertFalse(self.bi.build_index(self.root, content='all').get('failed'))
        self.assertFalse(self.calls, 'ordinary follow-up must not embed retained unchanged files')
        before = self._rows('two.py')
        (self.root / 'one.py').unlink()
        self.assertFalse(self.bi.build_index(self.root, files=[], content='all').get('failed'))
        self.assertEqual(generation, self._generation())
        self.assertTrue(self._rows('one.py')['chunks_code'])
        self.assertFalse(self.bi.build_index(self.root, files=[self.root / 'one.py'], content='all').get('failed'))
        self.assertFalse(self._rows('one.py')['chunks_code'])
        self.assertEqual(before, self._rows('two.py'))
        (self.root / 'two.py').unlink()
        self.assertFalse(self.bi.build_index(self.root, content='all').get('failed'))
        self.assertFalse(self._rows('two.py')['chunks_code'])

    def test_targeted_currency_refusal_precedes_store_mutation(self):
        # These cases isolate model identity/currency, not precision conversion.
        recorded_precision = self.bi._precision_class_from_version(
            _read_meta_store(self.root / '.wavefoundry' / 'index')['model_versions']['docs'])
        cases = [('full', None, None), ('walker', self.bi, 'WALKER_VERSION'),
                 ('docs_model', self.bi, 'DOCS_MODEL'), ('code_model', self.bi, 'CODE_MODEL'),
                 ('chunker', self.bi._get_chunker(), 'CHUNKER_VERSION'),
                 ('graph_builder', self.gi, 'GRAPH_BUILDER_VERSION'),
                 ('graph_schema', self.gi, 'GRAPH_SCHEMA_VERSION'),
                 ('graph_store_schema', self.gi, 'GRAPH_STORE_SCHEMA_VERSION'),
                 ('storage_schema', self.iss, 'STATE_STORE_SCHEMA_VERSION'),
                 ('policy', None, None)]
        for name, module, attr in cases:
            with self.subTest(name=name):
                before = self._rows('two.py')
                generation = self._generation()
                kwargs = {'full': True} if name == 'full' else {}
                if name == 'policy': kwargs['include_tests'] = True
                cm = patch.object(module, attr, 'incompatible') if module else contextlib.nullcontext()
                with cm, patch.object(self.bi, '_predicted_precision_class', return_value=recorded_precision), \
                     patch.object(self.iss.IndexStateStore, 'ensure_current', side_effect=AssertionError('mutation before refusal')) as ensure:
                    try:
                        result = self.bi.build_index(self.root, files=[self.root / 'one.py'], content='all', **kwargs)
                    except self.iss.index_compatibility.IndexCompatibilityError as exc:
                        result = {'failed': True, 'failure': str(exc), 'code': exc.code}
                self.assertTrue(result.get('failed'), result)
                self.assertIn('Reload/restart' if result.get('code') else 'complete walk', result['failure'])
                ensure.assert_not_called()
                self.assertEqual(before, self._rows('two.py'))
                self.assertEqual(generation, self._generation())

    def test_targeted_rechunk_preserves_unselected_and_idle_walk_certifies_policy(self):
        before = self._rows('two.py')
        result = self.bi.build_index(self.root, files=[self.root / 'one.py'], content='all', rechunk=True)
        self.assertFalse(result.get('failed'), result)
        self.assertEqual(before, self._rows('two.py'))
        # A policy change with identical membership still needs the complete
        # walk to record currency; the following targeted call may then run.
        self.assertFalse(self.bi.build_index(self.root, content='all', include_tests=True).get('failed'))
        result = self.bi.build_index(self.root, files=[], content='all', include_tests=True)
        self.assertFalse(result.get('failed'), result)

    def test_targeted_pending_storage_rebuild_refuses_before_mutation(self):
        import sqlite_storage_migration as migration
        before = self._rows('two.py')
        generation = self._generation()
        with patch.object(migration, 'require_ready'), \
             patch.object(migration, 'read_receipt', return_value={'state': 'rebuild_pending'}), \
             patch.object(migration, 'rebuild_requested', return_value=True), \
             patch.object(self.iss.IndexStateStore, 'ensure_current') as ensure:
            result = self.bi.build_index(self.root, files=[self.root / 'one.py'], content='all')
        self.assertTrue(result.get('failed'))
        self.assertIn('complete walk', result['failure'])
        ensure.assert_not_called()
        self.assertEqual(before, self._rows('two.py'))
        self.assertEqual(generation, self._generation())

    def test_owned_close_failure_preserves_original_error(self):
        original = KeyboardInterrupt('original')
        store = MagicMock()
        store.close.side_effect = OSError('close failed')
        try:
            try:
                raise original
            finally:
                self.bi._close_owned_build_store(store)
        except BaseException as exc:
            self.assertIs(exc, original)
        else:
            self.fail('original failure was swallowed')
        store.close.assert_called_once()

    def test_owned_build_handles_close_with_retained_failure_tracebacks(self):
        for fault in ('publication_cancel', 'changed_reconcile', 'idle_reconcile'):
            with self.subTest(fault=fault):
                (self.root / 'one.py').write_text('def one():\n    """Original documentation."""\n    return 1\n')
                # Repair any dirty attempt left by the previous injected failure.
                self.assertFalse(self.bi.build_index(self.root, full=True, content='all').get('failed'))
                before = self._rows('one.py')
                connections = []
                original_init = self.iss.IndexStateStore.__init__
                def capture(store, *args, **kwargs):
                    original_init(store, *args, **kwargs)
                    connections.append(store._conn)
                captured = []
                if fault != 'idle_reconcile': self._change_one()
                if fault == 'publication_cancel':
                    target, symbol = self.gi.GraphPublication, 'apply'
                    error = KeyboardInterrupt('retained cancellation')
                else:
                    target, symbol = self.bi, '_execute_orphan_store_reconcile'
                    error = OSError('retained reconciliation failure')
                def fail(*args, **kwargs):
                    try:
                        raise error
                    except BaseException as exc:
                        captured.append(exc.__traceback__)
                        raise
                with contextlib.ExitStack() as stack:
                    stack.enter_context(patch.object(self.iss.IndexStateStore, '__init__', capture))
                    stack.enter_context(patch.object(target, symbol, side_effect=fail))
                    if fault != 'publication_cancel':
                        stack.enter_context(patch.object(self.bi, '_plan_orphan_store_reconcile',
                            return_value={'graph': set(), 'file_freshness': {'orphan.py'}, 'secret_scan_cache': set()}))
                    try:
                        self.bi.build_index(self.root, content='all')
                    except BaseException as exc:
                        self.assertIs(exc, error)
                        captured.append(exc.__traceback__)
                    else:
                        self.fail('injected failure did not propagate')
                self.assertTrue(captured)
                self.assertTrue(connections)
                for conn in connections:
                    with self.assertRaises(Exception): conn.execute('SELECT 1').fetchone()
                with self.bi._index_build_lock(self.index_dir): pass
                after = self._rows('one.py')
                # Secrets cache is an optional pre-publication scanner resident,
                # not part of the semantic/graph publication transaction.
                before.pop('secret_scan_cache'); after.pop('secret_scan_cache')
                self.assertEqual(before, after)

    def test_published_graph_snapshot_pins_source_receipts_and_closes(self):
        old = self.gi.read_published_graph_snapshot(self.root)
        self.assertIsNotNone(old)
        original = self.gi.read_graph_payload_rows
        retained = []
        def interleave(conn, layer):
            retained.append(conn)
            payload = original(conn, layer)
            writer = self.iss.IndexStateStore(self.index_dir)
            try:
                with writer._conn:
                    writer._conn.execute("UPDATE graph_file_state SET source_hash='new-receipt' WHERE path='one.py'")
                    writer._conn.execute("UPDATE graph_nodes SET label='new-label' WHERE source_file='one.py'")
            finally: writer.close()
            return payload
        with patch.object(self.gi, 'read_graph_payload_rows', side_effect=interleave):
            snapshot = self.gi.read_published_graph_snapshot(self.root)
        self.assertEqual(old['source_hash'], snapshot['source_hash'])
        self.assertEqual(old['payload']['nodes'], snapshot['payload']['nodes'])
        with self.assertRaises(Exception): retained[0].execute('SELECT 1')
        def fail(conn, layer):
            retained.append(conn)
            raise OSError('read failed')
        with patch.object(self.gi, 'read_graph_payload_rows', side_effect=fail):
            self.assertIsNone(self.gi.read_published_graph_snapshot(self.root))
        with self.assertRaises(Exception): retained[-1].execute('SELECT 1')


if __name__ == "__main__":
    unittest.main()
