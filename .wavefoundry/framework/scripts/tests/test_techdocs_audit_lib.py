"""Wave 1vqqi / change 1vmt2: the TechDocs publication audit.

The fixtures here are deliberately not "the golden trio as shipped": the shipped
templates carry the generated-by marker, so a pristine trio emits
`techdocs_index_generated` and stripping only the landing page's marker makes the
trio mixed instead. The clean control therefore strips all three markers, which
is the state a repository is in once the workflow has authored its pages.
"""
from __future__ import annotations

import ast
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
import warnings
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import techdocs_audit_lib as audit  # noqa: E402

GOLDEN_EXCLUDE = [
    "/*",
    "!/index.md",
    "!/ARCHITECTURE.md",
    "!/architecture/",
    "!/architecture/**",
    "!/references/",
    "!/references/**",
    "!/prompts/",
    "/prompts/*",
    "!/prompts/index.md",
]

MKDOCS = """site_name: Example Documentation
docs_dir: docs
plugins:
  - techdocs-core
nav:
  - Home: index.md
  - Project overview: references/project-overview.md
  - Architecture: ARCHITECTURE.md
  - Workflow and agent commands: prompts/index.md
exclude_docs: |
""" + "".join(f"  {line}\n" for line in GOLDEN_EXCLUDE)

META = "Owner: Engineering\nStatus: active\nLast verified: 2026-08-18\n"


def _page(path: Path, title: str, body: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# {title}\n\n{META}\n{body}\n", encoding="utf-8")


def _build(root: Path, *, mkdocs: str | None = MKDOCS) -> None:
    """A minimal published tree whose trio is fully project-owned."""
    docs = root / "docs"
    _page(docs / "index.md", "Home")
    _page(docs / "ARCHITECTURE.md", "Architecture")
    _page(docs / "references" / "project-overview.md", "Project overview")
    _page(docs / "prompts" / "index.md", "Commands")
    _page(docs / "agents" / "guru.md", "Guru")  # excluded agent surface
    (root / "catalog-info.yaml").write_text("kind: Component\n", encoding="utf-8")
    if mkdocs is not None:
        (root / "mkdocs.yml").write_text(mkdocs, encoding="utf-8")


class TechdocsAuditFindingMatrixTests(unittest.TestCase):
    """AC-1: every code produced by exactly its injected defect, plus controls."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "repo"
        self.root.mkdir()
        _build(self.root)

    def _codes(self, report) -> list[str]:
        return [f.code for f in report.findings]

    def test_clean_tree_produces_no_finding(self):
        report = audit.audit_techdocs(self.root)
        self.assertEqual(self._codes(report), [], report.as_dict())
        self.assertEqual(report.publication["survivor_count"], 4)
        # Negative control for the clean control itself: the marker is what the
        # shipped templates carry, and adding it back must produce a finding.
        (self.root / "docs" / "index.md").write_text(
            "# Home\n\n" + META + "\n<!-- wavefoundry: generated missing-only Backstage/TechDocs "
            "baseline; project-owned, edit freely. -->\n",
            encoding="utf-8",
        )
        self.assertIn("techdocs_index_generated", self._codes(audit.audit_techdocs(self.root)))

    def test_a_nav_entry_that_escapes_docs_dir_is_reported_and_never_stat_ed(self):
        """`docs_root / "/etc/passwd"` IS `/etc/passwd`.

        With no containment check the join escaped, `is_file()` returned True
        and `excluded()` returned False, so neither branch fired: the audit
        silently accepted a path outside the root as a published nav target,
        falsifying the module's own "never reads outside the repository root".
        Containment is decided lexically so nothing outside is touched even to
        be rejected, which is asserted by spying on the stat path.
        """
        for entry in ("/etc/passwd", "../../../etc/passwd",
                      "/outside dir/page.md", "../../../outside dir/page.md"):
            with self.subTest(entry=entry):
                text = MKDOCS.replace("  - Home: index.md",
                                      f"  - Home: index.md\n  - Escape: {entry}")
                (self.root / "mkdocs.yml").write_text(text, encoding="utf-8")

                accessed_targets: list[tuple[str, str]] = []
                real_is_file = Path.is_file
                real_open = Path.open
                real_read_text = Path.read_text

                def spy_is_file(path, *args, **kwargs):  # noqa: ANN001
                    accessed_targets.append(("is_file", str(path)))
                    return real_is_file(path, *args, **kwargs)

                def spy_open(path, *args, **kwargs):  # noqa: ANN001
                    accessed_targets.append(("open", str(path)))
                    return real_open(path, *args, **kwargs)

                def spy_read_text(path, *args, **kwargs):  # noqa: ANN001
                    accessed_targets.append(("read_text", str(path)))
                    return real_read_text(path, *args, **kwargs)

                with unittest.mock.patch.object(Path, "is_file", spy_is_file), \
                        unittest.mock.patch.object(Path, "open", spy_open), \
                        unittest.mock.patch.object(Path, "read_text", spy_read_text):
                    report = audit.audit_techdocs(self.root)

                escapes = [f for f in report.findings
                           if f.code == "techdocs_nav_target_missing" and f.path == entry]
                self.assertTrue(escapes, "an escaping nav entry must be reported")
                self.assertIn("escapes docs_dir", escapes[0].detail)
                outside = [(operation, path) for operation, path in accessed_targets
                           if path.startswith("/etc/") or "outside dir" in path]
                self.assertEqual(
                    outside, [],
                    "nothing outside the root may be stat-ed, opened, or read",
                )

    def test_a_nav_symlink_escaping_the_root_degrades_before_is_file(self):
        """AC-9: enumeration and nav scoring must agree on an escaping symlink.

        The pre-repair audit filtered the link out of ``survivor_pages`` but then
        followed it through ``Path.is_file`` in the nav loop, emitted no finding or
        degrade, and could report clean. Spying on the logical link is the
        load-bearing assertion: ``is_file`` follows it to the external target.
        """
        if not hasattr(os, "symlink"):  # pragma: no cover
            self.skipTest("symlinks unavailable")
        outside = Path(self.tmp.name) / "outside target.md"
        _page(outside, "Outside")
        link = self.root / "docs" / "references" / "outside target.md"
        try:
            os.symlink(outside, link)
        except OSError:  # pragma: no cover
            self.skipTest("symlink creation not permitted")
        mkdocs = (self.root / "mkdocs.yml").read_text(encoding="utf-8")
        (self.root / "mkdocs.yml").write_text(
            mkdocs.replace("nav:\n", "nav:\n  - Outside: references/outside target.md\n", 1),
            encoding="utf-8",
        )

        real_is_file = Path.is_file
        real_open = Path.open
        real_read_text = Path.read_text
        target_accesses: list[tuple[str, Path]] = []

        def spy(path):
            target_accesses.append(("is_file", path))
            return real_is_file(path)

        def spy_open(path, *args, **kwargs):
            target_accesses.append(("open", path))
            return real_open(path, *args, **kwargs)

        def spy_read_text(path, *args, **kwargs):
            target_accesses.append(("read_text", path))
            return real_read_text(path, *args, **kwargs)

        with unittest.mock.patch.object(Path, "is_file", spy), \
                unittest.mock.patch.object(Path, "open", spy_open), \
                unittest.mock.patch.object(Path, "read_text", spy_read_text):
            report = audit.audit_techdocs(self.root)

        self.assertIn(audit.DEGRADE_NAV_TARGET_ESCAPES_ROOT, report.degraded)
        self.assertEqual(report.publication["unsafe_nav_targets"],
                         ["references/outside target.md"])
        self.assertNotEqual(report.summary["verdict"], audit.VERDICT_CLEAN)
        self.assertEqual(
            [operation for operation, path in target_accesses if path == link],
            [],
            "containment must refuse the link before is_file/open/content access",
        )

    def test_spaced_nav_targets_flow_through_raw_and_worker_audits(self):
        target = "decisions/1abc-adr architecture choice.md"
        mkdocs = MKDOCS.replace(
            "  - Home: index.md", f"  - Decision: '{target}'", 1).replace(
                "  !/references/**\n",
                "  !/references/**\n  !/decisions/\n  !/decisions/**\n",
                1,
            )
        (self.root / "mkdocs.yml").write_text(mkdocs, encoding="utf-8")
        page = self.root / "docs" / target
        _page(page, "Architecture choice")

        for runner in (audit.audit_techdocs, audit.run_techdocs_audit):
            with self.subTest(runner=runner.__name__, state="present"):
                report = runner(self.root)
                self.assertIn(target, report.publication["nav"])
                self.assertNotIn(audit.DEGRADE_MKDOCS_SHAPE, report.degraded)
                self.assertNotIn(
                    ("techdocs_nav_target_missing", target),
                    [(finding.code, finding.path) for finding in report.findings],
                )

        page.unlink()
        for runner in (audit.audit_techdocs, audit.run_techdocs_audit):
            with self.subTest(runner=runner.__name__, state="missing"):
                report = runner(self.root)
                self.assertIn(target, report.publication["nav"])
                self.assertNotIn(audit.DEGRADE_MKDOCS_SHAPE, report.degraded)
                self.assertIn(
                    ("techdocs_nav_target_missing", target),
                    [(finding.code, finding.path) for finding in report.findings],
                )

    def test_unmodelled_yaml_indicator_nav_values_degrade_through_public_paths(self):
        target = "decisions/1abc-adr architecture choice.md"
        for label, expression in (
            ("anchor", f"&adr {target}"),
            ("tag", f"!!str {target}"),
            ("flow sequence", f"[{target}]"),
            ("terminal colon", "target:"),
        ):
            mkdocs = MKDOCS.replace(
                "  - Home: index.md", f"  - Decision: {expression}", 1)
            (self.root / "mkdocs.yml").write_text(mkdocs, encoding="utf-8")
            for runner in (audit.audit_techdocs, audit.run_techdocs_audit):
                with self.subTest(form=label, runner=runner.__name__):
                    report = runner(self.root)
                    self.assertIn(audit.DEGRADE_MKDOCS_SHAPE, report.degraded)
                    self.assertNotIn(expression, report.publication["nav"])
                    self.assertNotIn(
                        ("techdocs_nav_target_missing", expression),
                        [(finding.code, finding.path) for finding in report.findings],
                    )

    def test_nav_target_missing_and_excluded_are_distinct(self):
        (self.root / "docs" / "ARCHITECTURE.md").unlink()
        codes = self._codes(audit.audit_techdocs(self.root))
        self.assertIn("techdocs_nav_target_missing", codes)
        self.assertNotIn("techdocs_nav_target_excluded", codes)

        _build(self.root)
        # A nav entry that exists but that `/prompts/*` removes: only index.md returns.
        _page(self.root / "docs" / "prompts" / "plan.md", "Plan")
        text = (self.root / "mkdocs.yml").read_text(encoding="utf-8")
        (self.root / "mkdocs.yml").write_text(
            text.replace("  - Workflow and agent commands: prompts/index.md",
                         "  - Workflow and agent commands: prompts/index.md\n  - Plan: prompts/plan.md"),
            encoding="utf-8",
        )
        report = audit.audit_techdocs(self.root)
        excluded = [f for f in report.findings if f.code == "techdocs_nav_target_excluded"]
        self.assertEqual([f.path for f in excluded], ["prompts/plan.md"])
        self.assertEqual(excluded[0].severity, audit.SEVERITY_HIGH)

    def test_link_codes_and_their_precedence(self):
        docs = self.root / "docs"
        _page(docs / "references" / "links.md", "Links", body="\n".join([
            "[excluded target](../agents/guru.md)",          # inside docs_dir, removed by exclude_docs
            "[outside docs_dir](../../catalog-info.yaml)",   # inside root, outside docs_dir
            "[missing](./nowhere.md)",                       # dangles inside the boundary
            "[dangling and excluded](../agents/gone.md)",    # both -> outside_boundary wins
        ]))
        report = audit.audit_techdocs(self.root)
        by_href = {f.href: f.code for f in report.findings if f.href}
        self.assertEqual(by_href["../agents/guru.md"], "techdocs_link_outside_boundary")
        self.assertEqual(by_href["../../catalog-info.yaml"], "techdocs_link_outside_boundary")
        self.assertEqual(by_href["./nowhere.md"], "techdocs_link_missing")
        # Precedence: a link that both dangles and is excluded reports the boundary code only.
        self.assertEqual(by_href["../agents/gone.md"], "techdocs_link_outside_boundary")

    def test_links_inside_code_fences_are_not_findings(self):
        docs = self.root / "docs"
        _page(docs / "references" / "fenced.md", "Fenced", body=(
            "```\n[dangling in a fence](./nope.md)\n```\n\nSome `[inline](./nope2.md)` text.\n"
        ))
        report = audit.audit_techdocs(self.root)
        self.assertEqual([f for f in report.findings if f.path == "references/fenced.md"], [])

    def test_percent_encoded_href_resolves(self):
        """Without the shared unquote this reads as a dangling link."""
        docs = self.root / "docs"
        _page(docs / "references" / "adr one.md", "ADR one")
        _page(docs / "references" / "cite.md", "Cite", body="[adr](./adr%20one.md)")
        report = audit.audit_techdocs(self.root)
        self.assertEqual([f for f in report.findings if f.path == "references/cite.md"], [])

    def test_metadata_incomplete_fires_on_a_survivor(self):
        (self.root / "docs" / "references" / "bare.md").write_text("# Bare\n", encoding="utf-8")
        report = audit.audit_techdocs(self.root)
        self.assertIn("techdocs_metadata_incomplete", self._codes(report))

    def test_a_malformed_verified_against_stamp_is_the_second_metadata_injection(self):
        """AC-1's other named metadata case, distinct from a missing block.

        `Verified against` is NOT the generated-by marker: that one is what
        `techdocs_index_generated` reports. This page has a complete metadata
        block and is still incomplete, so the finding cannot be coming from the
        missing-block path.
        """
        page = self.root / "docs" / "references" / "stamped.md"
        page.write_text(
            "# Stamped\n\n" + META + "Verified against: not-a-real-stamp\n\nbody\n",
            encoding="utf-8")
        report = audit.audit_techdocs(self.root)
        hits = [f for f in report.findings
                if f.code == "techdocs_metadata_incomplete"
                and f.path == "references/stamped.md"]
        self.assertTrue(hits, "a malformed stamp must be reported")
        self.assertIn("Verified against", hits[0].detail)
        self.assertNotIn("techdocs_index_generated", self._codes(report))

    def test_trio_partial_is_one_record_and_index_generated_is_independent(self):
        marker = "# wavefoundry: generated missing-only Backstage/TechDocs baseline; project-owned, edit freely.\n"
        (self.root / "catalog-info.yaml").write_text(marker + "kind: Component\n", encoding="utf-8")
        report = audit.audit_techdocs(self.root)
        partial = [f for f in report.findings if f.code == "techdocs_trio_partial"]
        self.assertEqual(len(partial), 1)
        self.assertEqual(partial[0].path, "mkdocs.yml")
        self.assertEqual(partial[0].severity, audit.SEVERITY_MEDIUM)
        # Independent facts: stamping the landing page too adds the second code.
        (self.root / "docs" / "index.md").write_text(
            "# Home\n\n" + META + "\n<!-- wavefoundry: generated missing-only Backstage/TechDocs "
            "baseline; project-owned, edit freely. -->\n", encoding="utf-8")
        codes = self._codes(audit.audit_techdocs(self.root))
        self.assertIn("techdocs_trio_partial", codes)
        self.assertIn("techdocs_index_generated", codes)

    def test_canonical_order_is_the_code_sequence_not_alphabetical(self):
        docs = self.root / "docs"
        (docs / "references" / "bare.md").write_text("# Bare\n", encoding="utf-8")
        _page(docs / "references" / "links.md", "Links", body="[missing](./nowhere.md)")
        (docs / "ARCHITECTURE.md").unlink()
        report = audit.audit_techdocs(self.root)
        codes = self._codes(report)
        self.assertEqual(codes, sorted(codes, key=audit.FINDING_ORDER.index))
        # Alphabetical would put link_missing before nav_target_missing; canonical does not.
        self.assertLess(codes.index("techdocs_nav_target_missing"), codes.index("techdocs_link_missing"))


class TechdocsAuditBoundaryAgreementTests(unittest.TestCase):
    """AC-2: agreement with the pinned oracle, scoped and guarded against being a copy check.

    The agreement claim covers the recorded golden corpus and its two mutants ONLY.
    It is deliberately NOT extended to generated pattern families: a readiness lane
    executed the oracle against real `git check-ignore` and found it diverges from
    gitignore semantics on `**/name.md` (which it fails to match at the root) and on
    internal-slash patterns (which it treats as floating rather than anchored), so a
    matcher implementing MkDocs semantics MUST disagree with it there. Those families
    are checked against git instead.
    """

    def _oracle(self):
        from tests.test_render_agent_surfaces import TechdocsExcludeDocsOracleTests as oracle
        return oracle

    def test_agrees_with_the_recorded_golden_corpus(self):
        oracle = self._oracle()
        for rel in oracle.SURVIVORS:
            self.assertFalse(audit.excluded(rel, GOLDEN_EXCLUDE), f"{rel} should survive")
        for rel in oracle.REJECTS:
            self.assertTrue(audit.excluded(rel, GOLDEN_EXCLUDE), f"{rel} should be excluded")

    def test_the_two_recorded_mutants_still_flip(self):
        without_prompts_star = [p for p in GOLDEN_EXCLUDE if p != "/prompts/*"]
        self.assertFalse(audit.excluded("prompts/plan-feature.prompt.md", without_prompts_star))
        without_index_reinclude = [p for p in GOLDEN_EXCLUDE if p != "!/index.md"]
        self.assertTrue(audit.excluded("index.md", without_index_reinclude))

    def test_the_oracle_does_not_import_the_shipped_library(self):
        """Otherwise the agreement collapses into one implementation checked against itself."""
        source = (SCRIPTS_ROOT / "tests" / "test_render_agent_surfaces.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        self.assertNotIn("techdocs_audit_lib", imported)

    def test_mkdocs_default_prepend_is_pinned_here_because_the_oracle_omits_it(self):
        # Against an EMPTY block, so only the defaults can be doing the work.
        # Asserting these against GOLDEN_EXCLUDE would pass vacuously: its
        # leading `/*` already removes all three, so emptying
        # MKDOCS_DEFAULT_EXCLUDES would not change a single verdict.
        self.assertTrue(audit.excluded(".hidden.md", []))
        self.assertTrue(audit.excluded("templates/page.md", []))
        self.assertTrue(audit.excluded("sub/.hidden.md", []))
        # A page the defaults do NOT touch, which keeps the assertions above
        # from passing merely because everything is excluded.
        self.assertFalse(audit.excluded("agents/guru.md", []))
        # And with a real block, an ordinary page is removed by the block itself.
        self.assertTrue(audit.excluded("agents/guru.md", GOLDEN_EXCLUDE))

    def test_a_malformed_character_class_matches_nothing_and_never_raises(self):
        """The class translation put raw text into re.compile.

        `re.error` derives from Exception alone, so it is caught by neither
        entry point's except tuple: a single bad pattern in a target's
        mkdocs.yml surfaced as a raised traceback instead of the tool's own
        error envelope. Such a pattern now matches NOTHING rather than being
        read literally: pathspec refuses it outright, so MkDocs cannot load
        the config at all and inventing a boundary for a file MkDocs would
        reject is the wrong answer. `unsupported_patterns` reports it.
        """
        for pattern in (r"[a\].md", r"[a\]b].md", r"[z-a].md", r"[a-\].md", "a[b.md"):
            with self.subTest(pattern=pattern):
                self.assertIsInstance(audit.excluded("a.md", [pattern]), bool)
        self.assertFalse(audit.excluded("[z-a].md", [r"[z-a].md"]))
        self.assertIn(r"[z-a].md", audit.unsupported_patterns([r"[z-a].md"]))

    def test_backslash_escapes_match_the_escaped_character(self):
        """Untranslated escapes silently under-excluded: the page stayed published."""
        for pattern, path in ((r"\a.md", "a.md"), (r"\*.md", "*.md"),
                              (r"a\*b.md", "a*b.md"), (r"\!a.md", "!a.md"),
                              (r"a\?c.md", "a?c.md")):
            with self.subTest(pattern=pattern):
                self.assertTrue(audit.excluded(path, [pattern]))
        # The escape is literal, so the wildcard meaning is gone.
        self.assertFalse(audit.excluded("axb.md", [r"a\*b.md"]))

    def test_the_classes_no_pattern_corpus_could_reach(self):
        """Four defects found only once the oracle was raised to MkDocs itself.

        Five rounds of ever-larger corpora were measured against `pathspec`,
        which answers "does this pattern match this path". This module claims to
        answer "which pages does the built site contain". Two of these four live
        in `mkdocs.structure.files` and are unreachable from ANY pathspec corpus
        at any size, with any pattern alphabet, which is why size kept not
        helping.
        """
        # 1. `dir/**/` matched nothing: dir_only disabled the direct tier while
        #    the body `dir/.*` could never match the ancestor name `dir`.
        for pattern in ("internal/**/", "/internal/**/", "**/internal/**/"):
            with self.subTest(pattern=pattern):
                self.assertTrue(audit.excluded("internal/notes.md", [pattern]))
        # ...and it must stay an ANCESTOR match, so a directory negation rescues
        # it, which is what MkDocs does and what dropping dir_only broke.
        self.assertFalse(audit.excluded("internal/notes.md",
                                        ["internal/**/", "!/internal/"]))

        # 2. `***` is not `**` to pathspec, and treating it as one published
        #    pages the built site hides.
        self.assertTrue(audit.excluded("sub/a.md", ["/**", "!/***"]))

        # 3. `draft_docs` removes pages from a BUILD. It is not modelled, and
        #    not READING it meant a page MkDocs omits was reported clean.
        parsed = audit.parse_mkdocs("docs_dir: docs\ndraft_docs: |\n  internal/\n")
        self.assertTrue(parsed["draft_docs_present"])

        # 4. MkDocs drops README.md when index.md sits beside it (same
        #    dest_uri). This repository already contains such a pair.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            (docs / "sub").mkdir(parents=True)
            for rel in ("index.md", "README.md", "sub/index.md", "sub/README.md", "sub/other.md"):
                _page(docs / rel, rel)
            survivors = audit.survivor_pages(root, docs, [])
            self.assertNotIn("README.md", survivors)
            self.assertNotIn("sub/README.md", survivors)
            self.assertIn("sub/other.md", survivors)

    def test_double_star_crosses_separators_in_every_spec_position(self):
        """The corpus axis that four earlier "0 disagreements" runs never had.

        gitignore gives `**` four positions: FIRST segment (`**/x`), LAST
        (`x/**`), MIDDLE (`a/**/b`), and ONLY (`**`, or `/**` once the anchor is
        stripped). This module had a branch for three of them, so the fourth
        compiled to `[^/]*` and matched only top-level names. In a multi-pattern
        block that demoted the match to the ancestor tier, where a later
        directory negation outranks it, and the deny-by-default `/**` +
        allowlist idiom silently published everything the allowlist re-included
        while `mkdocs build` really excluded it.

        Enumerated from the SPEC's positions rather than from the code's
        branches, which is the difference that found it: a corpus built from the
        families the implementation already models can only exercise what the
        code already thinks about.
        """
        for pattern in ("/**", "**"):
            with self.subTest(position="only", pattern=pattern):
                self.assertTrue(audit.excluded("public/deep/p.md", [pattern]))
                self.assertTrue(audit.excluded("top.md", [pattern]))
        self.assertTrue(audit.excluded("a/b/c.md", ["**/c.md"]))      # first
        self.assertTrue(audit.excluded("a/b/c.md", ["a/**"]))         # last
        self.assertTrue(audit.excluded("a/b/c.md", ["a/**/c.md"]))    # middle
        # A `**` that is NOT a whole segment stays a plain `*`.
        self.assertFalse(audit.excluded("a/b.md", ["a**b.md"]))

        # The end-to-end shape, which is what `mkdocs build` was run against:
        # the allowlist must not rescue a file the deny-all matched directly.
        block = ["/**", "!/index.md", "!/public/"]
        self.assertTrue(audit.excluded("public/index.md", block))
        self.assertTrue(audit.excluded("public/deep/p.md", block))
        self.assertFalse(audit.excluded("index.md", block))

    def test_a_directory_negation_cannot_rescue_a_directly_matched_file(self):
        """The shape that made the matcher fail OPEN on its own headline codes.

        `mkdocs build` emits both "included in the nav configuration, but this
        file is excluded from the built site" and "contains a link to ... which
        is excluded from the built site" for `/private/**` + `!/private/notes/`,
        while the audit reported the page as published and returned no findings
        at all. Publishing MORE than MkDocs is not the harmless direction: it is
        exactly what silences `techdocs_nav_target_excluded` (high) and
        `techdocs_link_outside_boundary` on a real 404.

        Both tiers are asserted together, because a fix for either one alone
        breaks the other: the first two cases must stay EXCLUDED (the exclusion
        matched the file directly) and the last two must stay PUBLISHED (it
        reached the file only through a directory).
        """
        self.assertTrue(audit.excluded("private/notes/x.md",
                                       ["/private/**", "!/private/notes/"]))
        self.assertTrue(audit.excluded("deep/x.md", ["**/*.md", "!deep/"]))
        self.assertFalse(audit.excluded("prompts/index.md", ["/*", "!/prompts/"]))
        self.assertFalse(audit.excluded("references/x.md", ["/*", "!/references/**"]))
        # A DIRECT negation beats an ancestor-only exclusion whatever the order.
        self.assertFalse(audit.excluded("references/x.md", ["!/references/**", "/*"]))
        self.assertFalse(audit.excluded("private/notes/x.md",
                                        ["/private/**", "!/private/notes/x.md"]))

    def test_the_backtracking_ceiling_is_measured_at_its_own_boundary(self):
        """Sampling only far above the ceiling cannot see the worst admitted case.

        The first version of this pin sampled 20, 26 and 40 groups, all refused
        before compilation, so its timing assertion could never observe the
        expensive side. The ceiling itself is the boundary value: a pattern AT
        the ceiling is admitted and must still be cheap, which is what makes the
        ceiling's value load-bearing rather than decorative.
        """
        import time

        # The literal, pinned. An earlier version of this test built its probe
        # as `shape * (_MAX_VARIABLE_GROUPS - 1)`, so the probe MOVED with the
        # constant it was meant to guard: raising the ceiling to 4 or to 5 left
        # it green, and only 7 turned it red, which admits the value 6 that the
        # library comment already records as measured wrong. A guard
        # parameterized by the thing it guards is not a guard.
        self.assertEqual(audit._MAX_VARIABLE_GROUPS, 3,
                         "the ceiling is a measured value, not a tunable; re-measure "
                         "the adversarial curve before changing it")

        # Adversarial shapes AT the ceiling, written out rather than generated,
        # so the pattern stays the same when the constant does not. Each carries
        # exactly three variable groups: `?` is fixed width, only `*` backtracks.
        subject = "a" * 60 + ".md"
        for at_ceiling in ("/*a*a*aX", "/*?*?*?x.md", "/*a*?*ax.md"):
            with self.subTest(at_ceiling=at_ceiling):
                self.assertEqual(audit.unsupported_patterns([at_ceiling]), [],
                                 "a pattern at the ceiling must be admitted")
                started = time.monotonic()
                audit.excluded(subject, [at_ceiling])
                self.assertLess(time.monotonic() - started, 0.05,
                                "the adversarial worst case AT the ceiling must stay "
                                "cheap; raising the ceiling re-opens the hang")

        # One group OVER the ceiling must be refused. This is the assertion that
        # dies when the ceiling rises, and it dies by FAILING rather than by
        # hanging: refusal happens during translation, so nothing is matched and
        # no time is spent. Timing assertions alone cannot fail safely here -- at
        # a ceiling of 20 the earlier pin ran past a sixty-second timeout instead
        # of reporting anything.
        for over_ceiling in ("/*a*a*a*aX", "/*?*?*?*?x.md"):
            with self.subTest(over_ceiling=over_ceiling):
                self.assertEqual(audit.unsupported_patterns([over_ceiling]), [over_ceiling],
                                 "one group over the ceiling must be refused, so the "
                                 "run degrades instead of paying the next step of the curve")

    def test_adjacent_floating_prefixes_collapse_without_reducing_source_budget(self):
        """Emission deduplication must not widen the admitted pattern boundary."""
        import time

        status, _, _, regex, _ = audit._translate_pattern("**/**/*aX")
        self.assertEqual(status, audit._PATTERN_OK)
        self.assertEqual(regex.pattern.count("(?:.*/)?"), 1)
        self.assertEqual(audit.unsupported_patterns(["**/**/*aX"]), [])
        self.assertEqual(audit.unsupported_patterns(["**/**/**/*aX"]), ["**/**/**/*aX"])

        subject = "/".join(["a"] * 1201)
        started = time.monotonic()
        self.assertFalse(audit.excluded(subject, ["**/**/*aX"]))
        self.assertLess(time.monotonic() - started, 0.5)

    def test_a_subject_that_cannot_name_a_file_is_never_matched(self):
        """The ceiling bounds the GROUP COUNT; cost is also cubic in SUBJECT length.

        `_page_findings` derives the subject from a markdown link href, which no
        filesystem bounds, so one published page carrying a 2500-character href
        against one ADMITTED pattern took 13.9s end to end through the CLI. The
        measured curve for the worst admitted pattern is 0.23ms at 60 characters,
        15.8ms at 255, 198ms at 600 and 900ms at 1000, so the ceiling alone never
        bounded this.

        A subject over the limits cannot name a file on any supported filesystem,
        so it can never be a published page; every caller that can reach here
        with an unbounded subject has an existence check behind it.
        """
        import time

        # The falsifier is an ANSWER difference, not a timing one, and it comes
        # first deliberately. A timing-only pin would not FAIL when the bound is
        # removed, it would HANG: at 20000 characters the unbounded cost is hours,
        # which is the same defect the ceiling pin above had. `/**` matches every
        # path, so without the short-circuit these are True and with it they are
        # False, decided in microseconds either way.
        over_component = "a" * (audit._MAX_COMPONENT_CHARS + 1)
        self.assertTrue(audit.excluded("a" * audit._MAX_COMPONENT_CHARS, ["/**"]),
                        "a representable subject is matched normally")
        self.assertFalse(audit.excluded(over_component, ["/**"]),
                         "a component no filesystem can hold is not a page to match")
        over_total = "/".join(["a" * 200] * 40)    # every component legal, total over cap
        self.assertGreater(len(over_total), audit._MAX_SUBJECT_CHARS)
        self.assertFalse(audit.excluded(over_total, ["/**"]))

        # Then the cost claim itself, on the worst ADMITTED pattern. Capped at a
        # length whose unbounded cost is seconds rather than hours, so a
        # regression here reports instead of wedging the suite.
        worst = "/*a*a*aX"
        self.assertEqual(audit.unsupported_patterns([worst]), [],
                         "the probe must use an ADMITTED pattern, or it proves nothing")
        for length in (audit._MAX_COMPONENT_CHARS + 1, 2500):
            with self.subTest(length=length):
                started = time.monotonic()
                self.assertFalse(audit.excluded("a" * length, [worst]))
                self.assertLess(time.monotonic() - started, 0.05,
                                "an unrepresentable subject must short-circuit before "
                                "the match, not after it")

    def test_a_segment_local_pattern_skips_the_ancestor_walk(self):
        """The length caps alone left the walk's cost unbounded, and a count cap was wrong.

        `excluded()` re-matches every pattern against each ancestor PREFIX, and
        every prefix begins with the same leading component, so cost is
        ancestors TIMES the per-component cost. A subject of one 250-character
        component followed by 1900 single-character components is legal under
        both length caps and cost 28.3 SECONDS for one admitted pattern.

        A 32-component CAP was tried first and was wrong: 33-deep trees are
        legal everywhere, so refusing them made `excluded()` answer "published"
        for an ordinary file, a silent fail-open under a comment claiming the
        subject could not name a file. The bound here is an exact equivalence
        instead: a regex that cannot match a separator can only ever match the
        first ancestor, because every deeper ancestor contains one.
        """
        import time

        # The equivalence must not change any answer. A deep path is scored
        # normally, which is what the count cap got wrong.
        deep = "/".join(["d%d" % n for n in range(32)]) + "/secret.md"
        self.assertGreater(len(deep.split("/")), 32)
        self.assertTrue(audit.excluded(deep, ["/**"]),
                        "a 33-component path is an ordinary file and must be scored, "
                        "not waved through")
        self.assertTrue(audit.excluded(deep, ["/d0/"]))
        self.assertFalse(audit.excluded(deep, ["/other/"]))
        self.assertTrue(audit.excluded(".hidden/" + deep, []),
                        "MkDocs' own default `.*` still applies at depth")

        # And it must bound the cost on the shape that cost 28.3 seconds.
        worst = "/a*?*?*?.md"
        self.assertEqual(audit.unsupported_patterns([worst]), [])
        self.assertFalse(audit._translate_pattern(worst)[4],
                         "the probe pattern must be segment-local, or it proves nothing")
        catastrophic = "a" * 250 + "/" + "/".join(["x"] * 1900)
        started = time.monotonic()
        self.assertFalse(audit.excluded(catastrophic, [worst]))
        # 0.15s is 2x the measured worst admitted cost under the two length
        # caps, found by adversarial search over 4 admitted patterns and 20
        # subject shapes: 66ms, from `/*a*a*aX` against a 1921-component
        # subject. The bound is deliberately stated from the search rather than
        # extrapolated from one point, which is how it was wrong three times.
        self.assertLess(time.monotonic() - started, 0.15,
                        "a segment-local pattern must not walk 1900 ancestors")

        # A separator-crossing pattern still walks every ancestor, or the
        # equivalence would be a silent narrowing rather than an optimization.
        self.assertTrue(audit._translate_pattern("**/d31/")[4])
        self.assertTrue(audit.excluded(deep, ["**/d31/"]))

    def test_separator_crossing_is_decided_by_the_compiled_class_not_by_syntax(self):
        """The ancestor equivalence is only sound if `crosses_separator` is exact.

        It was claimed exact and was not: `_class_end` forbids a LITERAL `/`
        inside a class, but `[!q]` compiles to `[^q]`, which matches `/`, and an
        ASCII range such as `[.-0]` spans it. Deciding segment-locality from
        syntax therefore skipped ancestors a crossing pattern really can match,
        which fails OPEN. Measured before the fix: 178 mismatches in 268590
        pairs against a full-walk reference, and 18 fail-opens against a real
        `mkdocs build`; after it, zero of both.
        """
        for pattern in ("/x[!q]y", "/x[^q]y", "/x[.-0]y", r"/a\\/b", "/prompts/*", "**/x.md"):
            with self.subTest(crossing=pattern):
                self.assertTrue(audit._translate_pattern(pattern)[4],
                                "a pattern whose regex can match a separator must be "
                                "walked against every ancestor")
        for pattern in ("/x[abc]y", "/a*?.md", "/*a*a*aX", "/index.md"):
            with self.subTest(segment_local=pattern):
                self.assertFalse(audit._translate_pattern(pattern)[4])
        # The behavioural consequence, which is what actually fails open: a
        # negated class landing on a separator position really does exclude the
        # subtree, and the audit must say so.
        self.assertTrue(audit.excluded("x/y/z.md", ["/x[!q]y/"]))
        self.assertTrue(audit.excluded("private/notes/n.md", ["/private[!q]notes/"]))
        self.assertFalse(audit.excluded("x/q/z.md", ["/x[!q]y/"]))

    def test_a_character_class_cannot_span_a_separator(self):
        """pathspec splits into SEGMENTS before it handles classes; `_class_end` did not.

        Scanning past `/` folded `[abc/[a-z]` into one Python class holding a
        separator, which matched almost any name where pathspec matched nothing.
        Measured against a real `mkdocs build`, the negated form published a site
        that is genuinely empty and the non-negated form over-excluded, with
        `degraded: []` either way.
        """
        # Unterminated within its own segment, so INERT: pathspec accepts the
        # config and the pattern matches nothing.
        self.assertEqual(audit.unsupported_patterns(["[abc/[a-z]*"]), [])
        self.assertFalse(audit.excluded("abc/index.md", ["[abc/[a-z]*"]))
        self.assertFalse(audit.excluded("index.md", ["[abc/[a-z]*"]))
        self.assertFalse(audit.excluded("references/x.md", ["[abc/[a-z]*"]))
        # A class that DOES close inside its segment still works, so the fix is
        # a segment boundary rather than a blanket refusal of classes.
        self.assertTrue(audit.excluded("a.md", ["[abc].md"]))
        self.assertTrue(audit.excluded("sub/b.md", ["sub/[abc].md"]))
        self.assertFalse(audit.excluded("d.md", ["[abc].md"]))

    def test_a_named_directory_double_star_keeps_its_anchor(self):
        """The `/**` strip removed the pattern's only slash before anchoring was decided.

        `sub/**/` therefore became the FLOATING `^(?:.*/)?sub$` and stopped
        excluding its own subtree, so two published pages went unchecked and a
        nav entry into them produced a false `techdocs_nav_target_excluded` at
        the top severity rank against a tree `mkdocs build --strict` accepts.
        The root-anchored form the earlier test used could not see it, because
        `/internal/**/` has a second slash the strip does not touch.
        """
        for pattern in ("sub/**/", "internal/**/"):
            name = pattern.split("/")[0]
            with self.subTest(pattern=pattern):
                self.assertTrue(audit.excluded(f"{name}/a.md", [pattern]))
                self.assertTrue(audit.excluded(f"{name}/deep/b.md", [pattern]))
                self.assertFalse(audit.excluded("index.md", [pattern]),
                                 "the pattern is anchored, so a same-named directory "
                                 "elsewhere must not be swept in")
                self.assertFalse(audit.excluded(f"agents/{name}/deep.md", [pattern]),
                                 "anchored means at docs_dir root, not floating")
        # The root-anchored forms that were already right must stay right.
        self.assertTrue(audit.excluded("internal/n.md", ["/internal/**/"]))
        self.assertTrue(audit.excluded("agents/internal/n.md", ["**/internal/**/"]))
        # One strip can leave another `/**` behind, so the strip repeats.
        self.assertTrue(audit.excluded("internal/n.md", ["/internal/**/**/"]))
        self.assertTrue(audit.excluded("internal/deep/m.md", ["/internal/**/**/"]))
        self.assertFalse(audit.excluded("index.md", ["/internal/**/**/"]))

    def test_a_bare_double_star_directory_does_not_publish_the_subtree(self):
        """`/**/` was the only fail-OPEN shape found in 1998 oracle-compared blocks.

        `rstrip("/")` left `/**`, the `dir/**/` normalization stripped the whole
        remainder, `anchored` computed False on the empty string, and the pattern
        compiled to a matcher for nothing. Against a real `mkdocs build` the tool
        then published seven pages the built site does not contain, including an
        agent surface and an unpublished tree, and did not degrade while doing it.

        Every neighbouring member of the family was already correct, which is why
        a corpus that walked the family generically missed this one: only the
        DEGENERATE case, where stripping leaves nothing behind, was wrong.
        """
        subtree = ["prompts/index.md", "references/deep/x.md", "a/b/c/d.md", "agents/guru.md"]
        for rel in subtree:
            with self.subTest(rel=rel, pattern="/**/"):
                self.assertTrue(audit.excluded(rel, ["/**/"]),
                                "`/**/` names every directory, so every page under one goes")
        for rel in ("index.md", "ARCHITECTURE.md"):
            with self.subTest(rel=rel, pattern="/**/"):
                self.assertFalse(audit.excluded(rel, ["/**/"]),
                                 "a root-level page has no ancestor directory to match")
        # A directory negation still cancels it, which is only expressible while
        # `/**/` stays an ancestor-tier directory match rather than a direct one.
        self.assertFalse(audit.excluded("prompts/index.md", ["/**/", "!/prompts/"]))
        # The neighbours that were already right must stay right.
        for pattern in ("**/", "dir/**/", "prompts/**/", "/prompts/**/", "**/internal/**/"):
            with self.subTest(neighbour=pattern):
                self.assertEqual(audit.unsupported_patterns([pattern]), [])
        self.assertTrue(audit.excluded("prompts/a.md", ["prompts/**/"]))
        self.assertFalse(audit.excluded("index.md", ["prompts/**/"]))

    def test_a_class_backslash_is_a_literal_member_not_an_escape(self):
        """`inner.replace("\\\\", "\\\\\\\\")` shipped with nothing able to fail on it.

        The test that named this repair asserted only `assertIsInstance(..., bool)`,
        which a REFUSED pattern satisfies exactly as well as a translated one, so
        reverting the doubling left the whole file green while `[a\\]` silently
        went from a live boundary to a degrade.
        """
        self.assertEqual(audit.unsupported_patterns(["[a\\].md"]), [],
                         "pathspec accepts this class, so the config loads and the "
                         "boundary must be computed rather than refused")
        self.assertTrue(audit.excluded("a.md", ["[a\\].md"]))
        self.assertTrue(audit.excluded("\\.md", ["[a\\].md"]),
                        "the backslash is a MEMBER of the class, matching itself")
        self.assertFalse(audit.excluded("b.md", ["[a\\].md"]))

    def test_a_negated_directory_cancels_an_ancestor_exclusion(self):
        """Pins the shape the shipped deny-by-default block depends on.

        `/*` prunes `prompts/`, and `!/prompts/` cancels that for everything
        under it. This agrees with pathspec, which is the matcher MkDocs
        actually uses, and it is the behaviour a negation-without-subtree-reach
        rewrite broke: the audit stopped seeing genuinely published pages.
        The complementary case (an exclusion that matched the FILE, where
        pathspec does NOT let a negated directory re-include it) is a recorded
        divergence rather than a pinned behaviour; see `_pattern_regex`.
        """
        without_prompts_star = [p for p in GOLDEN_EXCLUDE if p != "/prompts/*"]
        self.assertFalse(audit.excluded("prompts/plan-feature.prompt.md", without_prompts_star))
        self.assertFalse(audit.excluded("prompts/index.md", GOLDEN_EXCLUDE))
        self.assertTrue(audit.excluded("prompts/plan.md", GOLDEN_EXCLUDE))
        # An exact negation still re-includes its own file.
        self.assertFalse(audit.excluded("index.md", ["/*", "!index.md"]))

    def test_a_directory_pattern_never_matches_a_file_of_the_same_name(self):
        """DEL-2: `dir_only` was computed and then never used.

        A separate test rather than a git-oracle case, because a path cannot be
        both a directory and a regular file in one fixture.
        """
        self.assertTrue(audit.excluded("vendored/page.md", ["vendored/"]))
        self.assertFalse(audit.excluded("vendored", ["vendored/"]))
        # Without the trailing slash the same name does match the file.
        self.assertTrue(audit.excluded("vendored", ["vendored"]))

    def test_survivor_enumeration_and_the_matcher_agree_about_dotfiles(self):
        """DEL-2: two functions in one module must not disagree on one boundary."""
        self.assertFalse(audit.excluded(".keep.md", ["!.keep.md"]))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            docs.mkdir()
            (docs / ".keep.md").write_text("# Keep\n" + META, encoding="utf-8")
            (docs / "normal.md").write_text("# Normal\n" + META, encoding="utf-8")
            self.assertEqual(
                audit.survivor_pages(root, docs, ["!.keep.md"]),
                [".keep.md", "normal.md"])

    def test_external_oracle_agrees_on_single_pattern_families(self):
        """git check-ignore is the admissible external oracle for single-pattern semantics.

        It is NOT admissible for whole-block outcomes: git prunes excluded parent
        directories where MkDocs' matcher does not, so a re-include through an
        excluded parent diverges by construction. Only patterns with no such chain
        are compared here.
        """
        if shutil.which("git") is None:  # pragma: no cover - git is present in this repo's CI
            self.skipTest("git unavailable")
        cases = [
            ("*.log", ["a.log", "deep/b.log", "keep.md"]),
            ("build/", ["build/x.md", "nested/build/y.md", "buildish.md"]),
            ("docs/only.md", ["docs/only.md", "other/docs/only.md"]),
            ("**/deep.md", ["deep.md", "a/deep.md", "a/b/deep.md"]),
            # DEL-2: the two families the original corpus could not reach. Both
            # were wrong in BOTH directions before the repair, so each pattern
            # carries paths it must match and paths it must not.
            ("[abc].md", ["a.md", "c.md", "d.md", "a/b.md", "[abc].md"]),
            ("[!abc].md", ["d.md", "a.md"]),
            ("[a-c].md", ["b.md", "z.md"]),
            ("a**b.md", ["ab.md", "axb.md", "a/b.md", "a/x/b.md"]),
            ("**b.md", ["b.md", "xb.md", "a/b.md"]),
            # A trailing slash names a directory and everything under it.
            ("vendored/", ["vendored/page.md", "vendoredish.md"]),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
            for pattern, paths in cases:
                (repo / ".gitignore").write_text(pattern + "\n", encoding="utf-8")
                for rel in paths:
                    target = repo / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text("x", encoding="utf-8")
                    result = subprocess.run(
                        ["git", "-C", str(repo), "check-ignore", "-q", rel],
                        capture_output=True,
                    )
                    git_says = result.returncode == 0
                    self.assertEqual(
                        audit.excluded(rel, [pattern]), git_says,
                        f"pattern {pattern!r} path {rel!r}: git says ignored={git_says}",
                    )


class TechdocsAuditDegradeTests(unittest.TestCase):
    """AC-3: every way the audit can fail to compute is named, and none reads as clean."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "repo"
        self.root.mkdir()
        _build(self.root)

    def test_absent_mkdocs_is_not_applicable_and_still_reports_the_trio(self):
        (self.root / "mkdocs.yml").unlink()
        report = audit.audit_techdocs(self.root)
        self.assertEqual(report.summary["verdict"], audit.VERDICT_NOT_APPLICABLE)
        self.assertIn(audit.DEGRADE_MKDOCS_ABSENT, report.degraded)
        self.assertEqual(report.trio["members"]["catalog-info.yaml"], "project_owned")

    def test_absent_exclude_block_never_publishes_everything(self):
        text = (self.root / "mkdocs.yml").read_text(encoding="utf-8")
        trimmed = text.split("exclude_docs:")[0]
        (self.root / "mkdocs.yml").write_text(trimmed, encoding="utf-8")
        report = audit.audit_techdocs(self.root)
        self.assertIn(audit.DEGRADE_EXCLUDE_DOCS_ABSENT, report.degraded)
        self.assertEqual(report.publication["survivor_pages"], [])
        self.assertNotEqual(report.summary["verdict"], audit.VERDICT_CLEAN)

    def test_serialization_variants_all_parse(self):
        for header in ("exclude_docs: |", "exclude_docs: |-", "exclude_docs: |+"):
            text = MKDOCS.replace("exclude_docs: |", header)
            (self.root / "mkdocs.yml").write_text(text, encoding="utf-8")
            report = audit.audit_techdocs(self.root)
            self.assertNotIn(audit.DEGRADE_EXCLUDE_DOCS_ABSENT, report.degraded, header)
            self.assertEqual(report.publication["survivor_count"], 4, header)

    def test_canonical_yaml_serializations_parse_the_same_as_indented_ones(self):
        """DEL-1: a zero-indent block sequence is canonical YAML, not a shape failure.

        `nav:` followed by `- Home: index.md` in column 0 is what PyYAML and
        js-yaml emit by default, so this is the shape a target acquires the
        moment any tool rewrites its mkdocs.yml. A collector that stops at the
        first unindented line reads the whole file as empty while still
        reporting `clean`.
        """
        zero_nav = MKDOCS.replace("  - Home:", "- Home:").replace(
            "  - Project overview:", "- Project overview:").replace(
            "  - Architecture:", "- Architecture:").replace(
            "  - Workflow and agent commands:", "- Workflow and agent commands:")
        (self.root / "mkdocs.yml").write_text(zero_nav, encoding="utf-8")
        report = audit.audit_techdocs(self.root)
        self.assertEqual(len(report.publication["nav"]), 4)
        self.assertEqual(report.publication["survivor_count"], 4)
        self.assertNotIn(audit.DEGRADE_MKDOCS_SHAPE, report.degraded)

        block = MKDOCS.split("exclude_docs:")[0] + "exclude_docs:\n" + "".join(
            f"- {line!r}\n" for line in GOLDEN_EXCLUDE)
        (self.root / "mkdocs.yml").write_text(block, encoding="utf-8")
        report = audit.audit_techdocs(self.root)
        self.assertEqual(report.publication["exclude_docs"], GOLDEN_EXCLUDE)
        self.assertEqual(report.publication["survivor_count"], 4)

    def test_spaced_nav_scalar_and_depth_matrix_is_explicit(self):
        """The old ``\\S+`` leaf dies on spaces; every supported spelling must survive."""
        target = "decisions/1abc-adr architecture choice.md"
        spellings = {
            "plain": target,
            "single quoted": f"'{target}'   ",
            "double quoted": f'"{target}"   ',
        }
        for label, spelling in spellings.items():
            cases = {
                "root": f"nav:\n  - {spelling}\n",
                "one section": f"nav:\n  - Decisions:\n      - Choice: {spelling}\n",
            }
            for depth, text in cases.items():
                with self.subTest(spelling=label, depth=depth):
                    parsed = audit.parse_mkdocs(text)
                    self.assertTrue(parsed["shape_ok"], parsed)
                    self.assertEqual(parsed["nav"], [target])

        siblings = audit.parse_mkdocs(
            "nav:\n"
            "  - Home: index.md\n"
            "  - Decisions:\n"
            f"      - Choice: {target}\n"
            "  - Overview: references/project-overview.md\n"
        )
        self.assertTrue(siblings["shape_ok"], siblings)
        self.assertEqual(
            siblings["nav"],
            ["index.md", target, "references/project-overview.md"],
        )

    def test_unmodelled_nav_syntax_and_second_section_depth_degrade(self):
        """A naive ``.+`` tail/flattening repair cannot pass this negative matrix."""
        target = "decisions/1abc-adr architecture choice.md"
        cases = {
            "two sections": (
                "nav:\n  - Decisions:\n      - Active:\n"
                f"          - Choice: {target}\n"
            ),
            "mixed wrapper": f"nav:\n  - Choice: '{target}\"\n",
            "unmatched wrapper": f"nav:\n  - Choice: '{target}\n",
            "empty single quote": "nav:\n  - Choice: ''\n",
            "empty double quote": 'nav:\n  - Choice: ""\n',
            "trailing token": f"nav:\n  - Choice: '{target}' trailing\n",
            "separation comment": f"nav:\n  - Choice: {target} # current\n",
            "whole value comment": "nav:\n  - Choice: # target omitted\n",
            "doubled single quote": (
                "nav:\n  - Choice: 'decisions/1abc-adr architecture''s choice.md'\n"
            ),
            "double quoted escape": (
                'nav:\n  - Choice: "decisions/1abc-adr architecture\\\\ choice.md"\n'
            ),
            "anchor": f"nav:\n  - Choice: &adr {target}\n",
            "alias": "nav:\n  - Choice: *adr\n",
            "tag": f"nav:\n  - Choice: !!str {target}\n",
            "block scalar": "nav:\n  - Choice: |\n      target.md\n",
            "folded scalar": "nav:\n  - Choice: >\n      target.md\n",
            "flow sequence": f"nav:\n  - Choice: [{target}]\n",
            "flow mapping": f"nav:\n  - Choice: {{path: {target}}}\n",
            "directive": "nav:\n  - Choice: %TAG ! tag:example.com,2026:\n",
            "reserved at": f"nav:\n  - Choice: @{target}\n",
            "reserved backtick": f"nav:\n  - Choice: `{target}\n",
            "nested mapping tail": f"nav:\n  - Choice: {target}: nested\n",
            "terminal colon": "nav:\n  - Choice: target:\n",
            "sequence indicator": f"nav:\n  - Choice: - {target}\n",
        }
        for label, text in cases.items():
            with self.subTest(case=label):
                parsed = audit.parse_mkdocs(text)
                self.assertFalse(parsed["shape_ok"], parsed)
                self.assertNotIn(target, parsed["nav"])

        colon_control = audit.parse_mkdocs("nav:\n  - Choice: target:slug.md\n")
        self.assertTrue(colon_control["shape_ok"], colon_control)
        self.assertEqual(colon_control["nav"], ["target:slug.md"])

    def test_a_column_zero_comment_does_not_truncate_a_block(self):
        """A comment inside a block is ordinary, and truncating on it published everything.

        The shipped `mkdocs.template.yml` opens with a column-0 comment and
        tells the operator to edit freely, so this is the normal case. Reading
        `exclude_docs` as empty here yields `clean` over a boundary that
        publishes every agent surface, which is the outcome the
        `exclude_docs_absent` degrade exists to prevent.
        """
        block = (MKDOCS.split("exclude_docs:")[0]
                 + "exclude_docs:\n# keep internal notes off the public site\n"
                 + "".join(f"- {line!r}\n" for line in GOLDEN_EXCLUDE))
        (self.root / "mkdocs.yml").write_text(block, encoding="utf-8")
        report = audit.audit_techdocs(self.root)
        self.assertEqual(report.publication["exclude_docs"], GOLDEN_EXCLUDE)
        self.assertEqual(report.publication["survivor_count"], 4)
        self.assertNotIn("agents/guru.md", report.publication["survivor_pages"])

        commented_nav = MKDOCS.replace(
            "  - Home: index.md",
            "# added by the docs team\n  - Home: index.md")
        (self.root / "mkdocs.yml").write_text(commented_nav, encoding="utf-8")
        report = audit.audit_techdocs(self.root)
        self.assertEqual(len(report.publication["nav"]), 4)
        self.assertNotIn(audit.DEGRADE_MKDOCS_SHAPE, report.degraded)

    def test_an_inline_comment_ends_a_sequence_entry_but_not_a_block_scalar_line(self):
        """A commented deny-by-default entry silently failed open.

        In a block SEQUENCE ` #` opens a comment, so keeping it made the pattern
        match nothing and every excluded page became a survivor. In the block
        SCALAR form `#` is literal for YAML too, so it must be preserved there;
        the two forms are asserted together because fixing one by breaking the
        other would still pass a single-sided test.
        """
        parsed = audit.parse_mkdocs(
            "exclude_docs:\n  - /*      # deny by default\n  - '!index.md'\n")
        self.assertEqual(parsed["exclude_docs"], ["/*", "!index.md"])
        literal = audit.parse_mkdocs("exclude_docs: |\n  /*  # literal here\n")
        self.assertEqual(literal["exclude_docs"], ["/*  # literal here"])

    def test_a_repeated_key_is_last_wins(self):
        """Concatenating two blocks invented findings; guarded for every key, not just nav."""
        cases = {
            "nav": ("nav:\n  - Old: missing-old.md\nnav:\n  - Home: index.md\n",
                    "nav", ["index.md"]),
            "exclude_docs seq": ("exclude_docs:\n  - /old\nexclude_docs:\n  - /new\n",
                                 "exclude_docs", ["/new"]),
            "exclude_docs scalar": ("exclude_docs: /old\nexclude_docs: /new\n",
                                    "exclude_docs", ["/new"]),
            "exclude_docs block": ("exclude_docs: |\n  /old\nexclude_docs: |\n  /new\n",
                                   "exclude_docs", ["/new"]),
            "docs_dir": ("docs_dir: one\ndocs_dir: two\n", "docs_dir", "two"),
        }
        for label, (text, key, expected) in cases.items():
            with self.subTest(key=label):
                self.assertEqual(audit.parse_mkdocs(text)[key], expected)

    def test_a_byte_order_mark_does_not_hide_the_first_key(self):
        """MkDocs reads its own config as utf-8-sig; plain utf-8 bound the BOM to the key.

        The fixture leads with `exclude_docs` deliberately. Leading with
        `site_name` (a key the parser ignores) or with `docs_dir: docs` (whose
        value equals the default) cannot fail: reverting `utf-8-sig` to `utf-8`
        leaves both green, which is exactly how this test shipped vacuous.
        """
        reordered = ("exclude_docs: |\n" + "".join(f"  {line}\n" for line in GOLDEN_EXCLUDE)
                     + "site_name: Example Documentation\ndocs_dir: docs\n"
                     + "nav:\n  - Home: index.md\n"
                     + "  - Project overview: references/project-overview.md\n"
                     + "  - Architecture: ARCHITECTURE.md\n"
                     + "  - Workflow and agent commands: prompts/index.md\n")
        (self.root / "mkdocs.yml").write_text("\ufeff" + reordered, encoding="utf-8")
        report = audit.audit_techdocs(self.root)
        self.assertEqual(report.publication["exclude_docs"], GOLDEN_EXCLUDE)
        self.assertNotIn(audit.DEGRADE_EXCLUDE_DOCS_ABSENT, report.degraded)
        self.assertEqual(report.publication["survivor_count"], 4)

    def test_a_pathological_pattern_cannot_wedge_the_matcher(self):
        """`?*` repeated is exponential, and 52 bytes of it hung the tool indefinitely.

        `excluded()` runs once per survivor page, per nav target and per link.
        The public worker deadline is the aggregate backstop; this local refusal
        keeps known hostile translations from consuming it. Timed rather than
        merely asserted, because a fix that makes it merely slower would still
        pass a boolean check.
        """
        import time

        for count in (20, 26, 40):
            with self.subTest(groups=count):
                pattern = "?*" * count + "x.md"
                started = time.monotonic()
                self.assertFalse(audit.excluded("a" * 40 + ".md", [pattern]))
                self.assertLess(time.monotonic() - started, 0.5)
                self.assertEqual(audit.unsupported_patterns([pattern]), [pattern])
        # A realistic pattern is nowhere near the budget and must still translate.
        self.assertEqual(audit.unsupported_patterns(["/*", "!/references/**", "*.tmp.md"]), [])

    def test_the_bounded_runner_returns_a_timeout_report_and_isolates_the_worker(self):
        """AC-10: timeout is a normal degraded report, not an exception or hang."""
        timeout = subprocess.TimeoutExpired(cmd=["python", "worker"], timeout=10)
        with unittest.mock.patch("subprocess_util.isolated_run", side_effect=timeout) as run, \
             unittest.mock.patch.object(
                 audit, "_trio_state",
                 side_effect=AssertionError("timeout handling must not perform repository I/O"),
             ) as trio_state:
            report = audit.run_techdocs_audit(self.root)

        self.assertEqual(report.degraded, (audit.DEGRADE_AUDIT_TIMEOUT,))
        self.assertEqual(report.summary["verdict"], audit.VERDICT_DEGRADED)
        self.assertEqual(report.trio, {})
        self.assertEqual(report.publication, {})
        self.assertEqual(report.audience, {})
        trio_state.assert_not_called()
        kwargs = run.call_args.kwargs
        self.assertEqual(kwargs["timeout"], audit.TECHDOCS_AUDIT_TIMEOUT_SECONDS)
        self.assertTrue(kwargs["capture_output"])
        self.assertTrue(kwargs["text"])
        self.assertEqual(kwargs["env"]["PYTHONDONTWRITEBYTECODE"], "1")
        self.assertEqual(kwargs["env"]["PYTHONUTF8"], "1")
        request = __import__("json").loads(kwargs["input"])
        self.assertEqual(request["repo_root"], str(self.root))
        self.assertIsNone(request["compare_to"])

    def test_the_bounded_runner_kills_the_recorded_crossing_pattern_reproduction(self):
        """The surviving literal-separated 2001-component shape exceeds the worker budget."""
        import time

        slow_href = "a/" * 2000 + "aY"
        _page(self.root / "docs" / "references" / "slow.md", "Slow", f"[slow]({slow_href})")
        text = (self.root / "mkdocs.yml").read_text(encoding="utf-8")
        (self.root / "mkdocs.yml").write_text(
            text.replace("exclude_docs: |\n", "exclude_docs: |\n  **/a/**/*aX\n", 1),
            encoding="utf-8",
        )
        before = {
            str(path.relative_to(self.root)): path.read_bytes()
            for path in self.root.rglob("*") if path.is_file() and not path.is_symlink()
        }

        started = time.monotonic()
        report = audit.run_techdocs_audit(self.root, timeout_seconds=0.2)
        elapsed = time.monotonic() - started

        self.assertEqual(report.degraded, (audit.DEGRADE_AUDIT_TIMEOUT,))
        self.assertLess(elapsed, 2.0, "the worker must be terminated near the configured budget")
        after = {
            str(path.relative_to(self.root)): path.read_bytes()
            for path in self.root.rglob("*") if path.is_file() and not path.is_symlink()
        }
        self.assertEqual(after, before, "timing out the read-only worker must not change the tree")

    def test_a_non_timeout_worker_failure_remains_could_not_run(self):
        completed = subprocess.CompletedProcess(
            args=["python", "worker"], returncode=3, stdout="", stderr="worker broke",
        )
        with unittest.mock.patch("subprocess_util.isolated_run", return_value=completed):
            with self.assertRaisesRegex(RuntimeError, "worker exited 3"):
                audit.run_techdocs_audit(self.root)

    def test_a_nested_set_warning_is_refused_the_same_way_under_any_filter(self):
        """`re` WARNS about `[[:alpha:]]` by default and RAISES it under -W error.

        FutureWarning is not an OSError, ValueError or re.error, so it escaped
        every enumerated tuple; escalating the warning locally makes the outcome
        identical however the host was launched, instead of leaking to stderr.
        """
        for pattern in ("[[:alpha:]]", "[[]]", "[a--b]", "[a&&b]"):
            with self.subTest(pattern=pattern):
                with warnings.catch_warnings():
                    warnings.simplefilter("error")
                    self.assertFalse(audit.excluded("a.md", [pattern]))
                    self.assertEqual(audit.unsupported_patterns([pattern]), [pattern])

    def test_inert_patterns_do_not_degrade_but_refused_ones_do(self):
        """Measured against pathspec, not assumed.

        An unterminated class is ACCEPTED by pathspec and matches nothing, so
        the config loads and the boundary is correct; degrading on it wrongly
        failed a buildable site. Only what pathspec cannot compile, or what this
        module cannot translate safely, is refused.
        """
        for pattern in ("a[b.md", "[abc", "[", "[!", "[]", "x[a-"):
            with self.subTest(inert=pattern):
                self.assertEqual(audit.unsupported_patterns([pattern]), [])
        for pattern in ("[z-a].md", "!", "trail\\"):
            with self.subTest(refused=pattern):
                self.assertEqual(audit.unsupported_patterns([pattern]), [pattern])
        # A bare `/` and any consecutive-slash run are REFUSED, not inert. `/`
        # was recorded as inert on a pathspec-only measurement, which answered a
        # lower-level question than the one the tool asks: `/` alone does match
        # nothing, but `!/` is a live RE-INCLUDE, and `/*` + `!/` publishes every
        # subtree page at both the pathspec and the `get_files` layer while this
        # module excluded all of them. `**//` and `/*//` were the same shape from
        # the other direction: `rstrip("/")` collapsed the run and left a matcher
        # a segment too wide. Refusing degrades the run instead of presenting a
        # boundary that measurement says is wrong.
        for pattern in ("/", "//", "!/", "!//", "**//", "/*//", "a//b.md"):
            with self.subTest(refused_degenerate=pattern):
                self.assertEqual(audit.unsupported_patterns([pattern]), [pattern])
        # Comments and blanks are inert too, which is what the filter is for.
        self.assertEqual(audit.unsupported_patterns(["# comment", "   ", ""]), [])

    def test_escaped_separator_refusal_matches_the_pinned_oracle_table(self):
        """Only a backslash that reaches the escape branch may refuse `/`."""
        oracle_refused = (
            r"/a\/b", r"a\/b", r"!a\/b", r"a\/b/", r"pre\/post.md",
            r"\/a", r"**/a\/b", r"a/\/b", r"a\\\/b",
        )
        accepted_controls = (r"a\\/b", r"\\/x.md", r"a\\/b/c", r"x/\\/y")

        self.assertEqual(len(oracle_refused), 9)
        for pattern in oracle_refused:
            with self.subTest(oracle_refused=pattern):
                self.assertEqual(audit._translate_pattern(pattern)[0], audit._PATTERN_REFUSED)
                self.assertEqual(audit.unsupported_patterns([pattern]), [pattern])
        for pattern in accepted_controls:
            with self.subTest(oracle_accepted=pattern):
                self.assertEqual(audit._translate_pattern(pattern)[0], audit._PATTERN_OK)
                self.assertEqual(audit.unsupported_patterns([pattern]), [])

        text = (self.root / "mkdocs.yml").read_text(encoding="utf-8")
        block = "\n".join(f"  {pattern}" for pattern in oracle_refused)
        (self.root / "mkdocs.yml").write_text(
            text.rstrip("\n") + "\n" + block + "\n", encoding="utf-8")
        report = audit.audit_techdocs(self.root)
        self.assertIn(audit.DEGRADE_MKDOCS_SHAPE, report.degraded)
        self.assertEqual(report.publication["unsupported_patterns"],
                         list(oracle_refused))

    def test_an_untranslatable_pattern_matches_nothing_and_degrades(self):
        """pathspec refuses these outright, so MkDocs cannot load the config at all.

        Matching nothing silently would narrow the boundary without saying so,
        which is the same silent-truncation shape as reading a block partially.
        """
        # `a[b.md` is INERT, not refused: pathspec accepts it and it matches
        # nothing, so the config still loads. Only what pathspec cannot compile
        # belongs here; the earlier expectation encoded a premise measurement
        # disproved.
        self.assertEqual(audit.unsupported_patterns(["/*", "[z-a].md", "a[b.md", "!ok.md"]),
                         ["[z-a].md"])
        self.assertFalse(audit.excluded("[.md", ["[.md"]))
        text = MKDOCS.split("exclude_docs:")[0] + "exclude_docs: |\n  /*\n  [z-a].md\n"
        (self.root / "mkdocs.yml").write_text(text, encoding="utf-8")
        report = audit.audit_techdocs(self.root)
        self.assertIn(audit.DEGRADE_MKDOCS_SHAPE, report.degraded)
        self.assertNotEqual(report.summary["verdict"], audit.VERDICT_CLEAN)

    def test_quoted_top_level_keys_are_recognized(self):
        """An unrecognized key parsed to an empty nav with the shape still reported ok."""
        text = MKDOCS.replace("docs_dir: docs", '"docs_dir": docs').replace("nav:", '"nav":', 1)
        (self.root / "mkdocs.yml").write_text(text, encoding="utf-8")
        report = audit.audit_techdocs(self.root)
        self.assertEqual(len(report.publication["nav"]), 4)
        self.assertEqual(report.publication["docs_dir"], "docs")

    def test_a_quoted_scalar_spanning_lines_degrades_rather_than_truncating(self):
        """DEL-1: keeping only the first line silently collapses the boundary."""
        text = MKDOCS.split("exclude_docs:")[0] + 'exclude_docs: "/*\n!index.md"\n'
        (self.root / "mkdocs.yml").write_text(text, encoding="utf-8")
        report = audit.audit_techdocs(self.root)
        self.assertIn(audit.DEGRADE_MKDOCS_SHAPE, report.degraded)
        self.assertNotEqual(report.summary["verdict"], audit.VERDICT_CLEAN)
        # The block is present but unread, so absence must NOT also be claimed.
        self.assertNotIn(audit.DEGRADE_EXCLUDE_DOCS_ABSENT, report.degraded)
        self.assertEqual(report.publication["survivor_pages"], [])

    def test_a_multiline_single_quoted_scalar_with_doubled_quote_degrades(self):
        """DEL-8: ``''`` is an escaped quote, not the scalar's closing quote."""
        text = MKDOCS.split("exclude_docs:")[0] + "exclude_docs: 'foo''\n  bar'\n"
        parsed = audit.parse_mkdocs(text)
        self.assertFalse(parsed["shape_ok"])
        self.assertEqual(parsed["exclude_docs"], None)

        (self.root / "mkdocs.yml").write_text(text, encoding="utf-8")
        report = audit.audit_techdocs(self.root)
        self.assertIn(audit.DEGRADE_MKDOCS_SHAPE, report.degraded)
        self.assertEqual(report.publication["survivor_pages"], [])

    def test_a_nav_section_header_is_not_a_nav_target(self):
        """DEL-1: `- Guides:` names no file; treating it as one emits a bogus finding."""
        nested = MKDOCS.replace(
            "  - Workflow and agent commands: prompts/index.md",
            "  - Guides:\n    - Commands: prompts/index.md")
        (self.root / "mkdocs.yml").write_text(nested, encoding="utf-8")
        report = audit.audit_techdocs(self.root)
        self.assertNotIn("Guides:", report.publication["nav"])
        self.assertIn("prompts/index.md", report.publication["nav"])
        self.assertEqual([f.path for f in report.findings
                          if f.code == "techdocs_nav_target_missing"], [])

    def test_flow_sequence_exclude_docs_degrades_without_crashing(self):
        text = MKDOCS.split("exclude_docs:")[0] + 'exclude_docs: ["/*", "!/index.md"]\n'
        (self.root / "mkdocs.yml").write_text(text, encoding="utf-8")
        report = audit.audit_techdocs(self.root)
        self.assertIn(audit.DEGRADE_MKDOCS_SHAPE, report.degraded)

    def test_docs_dir_escaping_the_root_is_refused_before_any_read(self):
        outside = Path(self.tmp.name) / "outside"
        outside.mkdir()
        # The sentinel MUST sit at a path that would survive the golden block if
        # containment failed. At `outside/sentinel.md` its docs_dir-relative
        # path is `sentinel.md`, which `/*` removes, so the page would never be
        # opened however completely containment failed and the assertion below
        # would hold vacuously. `!/references/**` re-includes this one.
        sentinel = outside / "references" / "sentinel.md"
        sentinel.parent.mkdir(parents=True, exist_ok=True)
        sentinel.write_text("# Sentinel\n" + META, encoding="utf-8")
        text = MKDOCS.replace("docs_dir: docs", "docs_dir: ../outside")
        (self.root / "mkdocs.yml").write_text(text, encoding="utf-8")

        # "Unread" is proved by instrumenting the read path, not by unchanged bytes:
        # a read leaves no filesystem trace, so a bytes assertion passes vacuously.
        opened: list[str] = []
        real_open = Path.open

        def spy(self, *args, **kwargs):  # noqa: ANN001
            opened.append(os.path.realpath(str(self)))
            return real_open(self, *args, **kwargs)

        Path.open = spy  # type: ignore[assignment]
        try:
            report = audit.audit_techdocs(self.root)
        finally:
            Path.open = real_open  # type: ignore[assignment]

        self.assertIn(audit.DEGRADE_DOCS_DIR_ESCAPES_ROOT, report.degraded)
        self.assertNotIn(os.path.realpath(str(sentinel)), opened)
        self.assertEqual(report.publication["survivor_pages"], [])

    def test_a_symlinked_file_escaping_the_root_is_refused(self):
        """The case the containment guards actually decide.

        `rglob` does not descend a symlinked DIRECTORY on any supported version
        (3.11 checks `is_dir(follow_symlinks=False)`, 3.13 defaults
        `recurse_symlinks=False`), so a directory-symlink fixture is refused by
        pathlib and pins nothing about this module. It does yield a symlinked
        FILE, and that is what the guard bounds. The link is placed under
        `references/`, which the golden block re-includes, so exclusion cannot
        mask a containment failure.
        """
        if not hasattr(os, "symlink"):  # pragma: no cover
            self.skipTest("symlinks unavailable")
        outside = Path(self.tmp.name) / "outside"
        outside.mkdir()
        leaked = outside / "leaked.md"
        leaked.write_text("# Leaked\n" + META, encoding="utf-8")
        link = self.root / "docs" / "references" / "leaked.md"
        try:
            os.symlink(leaked, link)
        except OSError:  # pragma: no cover
            self.skipTest("symlink creation not permitted")

        self.assertIn(link, set((self.root / "docs").rglob("*.md")),
                      "precondition: rglob must yield the symlinked file for the guard to matter")
        index = self.root / "docs" / "index.md"
        index.write_text(index.read_text(encoding="utf-8")
                         + "\n[Leak](references/leaked.md)\n", encoding="utf-8")
        touched: list[tuple[str, str]] = []
        real_is_file = Path.is_file
        real_open = Path.open

        def spy_is_file(self):  # noqa: ANN001
            touched.append(("is_file", os.path.realpath(str(self))))
            return real_is_file(self)

        def spy_open(self, *args, **kwargs):  # noqa: ANN001
            touched.append(("open", os.path.realpath(str(self))))
            return real_open(self, *args, **kwargs)

        Path.is_file = spy_is_file  # type: ignore[assignment]
        Path.open = spy_open  # type: ignore[assignment]
        try:
            report = audit.audit_techdocs(self.root)
        finally:
            Path.is_file = real_is_file  # type: ignore[assignment]
            Path.open = real_open  # type: ignore[assignment]
        self.assertNotIn("references/leaked.md", report.publication["survivor_pages"])
        self.assertEqual(report.publication["survivor_count"], 4)
        self.assertEqual(report.publication["unsafe_survivor_targets"],
                         ["references/leaked.md"])
        self.assertIn(audit.DEGRADE_SURVIVOR_TARGET_ESCAPES_ROOT, report.degraded)
        self.assertNotEqual(report.summary["verdict"], audit.VERDICT_CLEAN)
        outside = [finding for finding in report.findings
                   if finding.code == "techdocs_link_outside_boundary"
                   and finding.href == "references/leaked.md"]
        self.assertEqual(len(outside), 1)
        self.assertNotIn(str(leaked), str(report.as_dict()))
        self.assertNotIn(os.path.realpath(str(leaked)),
                         [path for operation, path in touched
                          if operation in {"is_file", "open"}])

        public = audit.run_techdocs_audit(self.root, timeout_seconds=2)
        self.assertEqual(public.publication["unsafe_survivor_targets"],
                         ["references/leaked.md"])
        self.assertIn(audit.DEGRADE_SURVIVOR_TARGET_ESCAPES_ROOT, public.degraded)
        self.assertTrue(any(finding.code == "techdocs_link_outside_boundary"
                            and finding.href == "references/leaked.md"
                            for finding in public.findings))

    def test_the_realpath_backstop_refuses_a_docs_root_that_escapes(self):
        """Isolates the SECOND containment guard, which nothing else reaches.

        There is no blanket symlink refusal any more, so the realpath comparison
        is the only containment guard and is reached on every candidate. Calling
        `survivor_pages` directly with a symlinked `docs_root` is the one route
        to it: the children are ordinary files whose realpath still escapes.
        Without this case either guard could be deleted alone with a green
        suite, which is how a defense layer disappears silently.
        """
        if not hasattr(os, "symlink"):  # pragma: no cover
            self.skipTest("symlinks unavailable")
        outside = Path(self.tmp.name) / "outside_root"
        (outside / "references").mkdir(parents=True)
        (outside / "references" / "leaked.md").write_text("# Leaked\n" + META, encoding="utf-8")
        link = self.root / "docs_linked"
        try:
            os.symlink(outside, link)
        except OSError:  # pragma: no cover
            self.skipTest("symlink creation not permitted")

        pages = sorted(p.name for p in link.rglob("*.md"))
        self.assertEqual(pages, ["leaked.md"],
                         "precondition: the walk must reach the escaped file")
        self.assertFalse((link / "references" / "leaked.md").is_symlink(),
                         "precondition: the child is a regular file, so is_symlink cannot decide it")
        self.assertEqual(audit.survivor_pages(self.root, link, GOLDEN_EXCLUDE), [])

    def test_an_in_root_symlink_is_published_like_mkdocs_publishes_it(self):
        """MkDocs follows symlinks; refusing them under-enumerated the site.

        `mkdocs.structure.files.get_files` walks with `followlinks=True`, so
        `docs/alias.md -> docs/real.md` really is two published pages. The
        earlier version of this test asserted the OPPOSITE and called MkDocs'
        behaviour a defect, which made a fail-open divergence look like a
        feature: a page the audit never enumerates is a page whose links and
        metadata are never checked.
        """
        if not hasattr(os, "symlink"):  # pragma: no cover
            self.skipTest("symlinks unavailable")
        real = self.root / "docs" / "references" / "real.md"
        _page(real, "Real")
        try:
            os.symlink(real, self.root / "docs" / "references" / "alias.md")
        except OSError:  # pragma: no cover
            self.skipTest("symlink creation not permitted")
        survivors = audit.survivor_pages(self.root, self.root / "docs", GOLDEN_EXCLUDE)
        self.assertIn("references/real.md", survivors)
        self.assertIn("references/alias.md", survivors)


    def test_a_symlink_cycle_terminates_in_bounded_time(self):
        """A cyclic docs tree must not hang the walk, in ANY topology.

        The first guard tested self-ancestry only, which catches
        `docs/loop -> docs` and nothing else. A two-node MUTUAL alias enumerated
        33 paths for 3 real files and terminated only on the OS symlink limit;
        a three-node branching alias did not terminate at all. Both topologies
        are asserted here with a wall-clock bound, because the failure mode is
        non-termination and a boolean assertion cannot see it.
        """
        if not hasattr(os, "symlink"):  # pragma: no cover
            self.skipTest("symlinks unavailable")
        import time

        for topology in ("mutual", "branching"):
            with self.subTest(topology=topology):
                base = Path(self.tmp.name) / f"cyc_{topology}"
                docs = base / "docs"
                (docs / "a").mkdir(parents=True)
                (docs / "b").mkdir()
                _page(docs / "a" / "p.md", "A")
                _page(docs / "b" / "q.md", "B")
                _page(docs / "index.md", "I")
                try:
                    if topology == "mutual":
                        os.symlink(docs / "b", docs / "a" / "link")
                        os.symlink(docs / "a", docs / "b" / "link")
                    else:
                        (docs / "c").mkdir()
                        _page(docs / "c" / "r.md", "C")
                        os.symlink(docs / "b", docs / "a" / "link")
                        os.symlink(docs / "c", docs / "b" / "link")
                        os.symlink(docs / "a", docs / "c" / "link")
                except OSError:  # pragma: no cover
                    self.skipTest("symlink creation not permitted")

                started = time.monotonic()
                survivors = audit.survivor_pages(base, docs, [])
                self.assertLess(time.monotonic() - started, 5.0,
                                "a symlink cycle must terminate quickly")
                # Bounded, and every real page still reported once.
                self.assertLess(len(survivors), 16)
                for real in ("index.md", "a/p.md", "b/q.md"):
                    self.assertIn(real, survivors)

    def test_the_symlink_matrix_matches_mkdocs_except_where_containment_refuses(self):
        """Enumeration must walk the way MkDocs walks, and stop where we differ.

        `mkdocs.structure.files.get_files` uses `os.walk(..., followlinks=True)`.
        `followlinks` governs DIRECTORY recursion; symlinked FILES are yielded
        either way. An earlier repair followed files only and cited `followlinks`
        as the reason, so it fixed the half that did not need it and left in-root
        symlinked DIRECTORIES undescended -- under-enumeration inside the root,
        where a page the audit never sees is never checked at all.

        Four cases, asserted together because fixing one alone regresses another.
        """
        if not hasattr(os, "symlink"):  # pragma: no cover
            self.skipTest("symlinks unavailable")
        outside = Path(self.tmp.name) / "beyond_root"
        outside.mkdir()
        _page(outside / "secret.md", "Secret")
        docs = self.root / "docs"
        _page(docs / "references" / "real.md", "Real")
        try:
            os.symlink(docs / "references", docs / "references_alias")   # in-root dir
            os.symlink(outside, docs / "references" / "escape")          # escaping dir
            os.symlink(outside / "secret.md", docs / "references" / "leak.md")  # escaping file
            os.symlink(docs, docs / "loop")                              # cycle
        except OSError:  # pragma: no cover
            self.skipTest("symlink creation not permitted")

        # No exclusion block: this pins ENUMERATION, and the golden block would
        # remove the top-level alias for an unrelated reason.
        survivors = audit.survivor_pages(self.root, docs, [])
        self.assertIn("references/real.md", survivors)
        self.assertIn("references_alias/real.md", survivors,
                      "MkDocs descends an in-root symlinked directory; so must we")
        self.assertFalse([p for p in survivors if "escape/" in p],
                         "a directory symlink leaving the root is refused")
        self.assertNotIn("references/leak.md", survivors,
                         "a file symlink leaving the root is refused")
        # The cycle must terminate; reaching this assertion at all proves it.
        self.assertTrue(survivors)

    def test_only_the_modelled_block_scalar_headers_are_read_as_patterns(self):
        """The five-member allowlist was wrong at BOTH ends, and both ends failed open.

        Fall-through: an indentation indicator (`|2`) missed the allowlist,
        reached the single-line-scalar branch, and became a one-element pattern
        list holding the HEADER TOKEN with shape_ok true and no degrade, so the
        operator's whole exclusion block was discarded and an unpublished tree was
        reported as published. PyYAML emits `|2` exactly when the block's first
        content line carries leading whitespace.

        Allowlist: `>` and `>-` were IN it and read line-per-pattern, but YAML
        FOLDS them into one space-joined scalar, so a two-line block became one
        pattern matching nothing and the audit emitted false findings against a
        tree `mkdocs build --strict` accepts.
        """
        body = "site_name: Example Documentation\ndocs_dir: docs\nexclude_docs: %s\n  /references/\n"
        for header in ("|", "|-", "|+"):
            with self.subTest(modelled=header):
                parsed = audit.parse_mkdocs(body % header)
                self.assertTrue(parsed["shape_ok"])
                self.assertEqual(parsed["exclude_docs"], ["/references/"])
        for header in ("|2", "|-2", "|2-", ">", ">-", ">+", ">+2", "|3"):
            with self.subTest(unmodelled=header):
                parsed = audit.parse_mkdocs(body % header)
                self.assertFalse(parsed["shape_ok"],
                                 "an unmodelled block-scalar header must degrade")
                self.assertNotEqual(parsed["exclude_docs"], [header],
                                    "the header token must never become a pattern")
        (self.root / "mkdocs.yml").write_text(body % "|2", encoding="utf-8")
        report = audit.audit_techdocs(self.root)
        self.assertIn(audit.DEGRADE_MKDOCS_SHAPE, report.degraded)
        self.assertNotEqual(report.summary["verdict"], audit.VERDICT_CLEAN)

    def test_a_nav_entry_is_scored_the_way_mkdocs_normalizes_it(self):
        """MkDocs normalizes through `get_file_from_path`; scoring the raw string did not.

        Two failures, opposite directions, from one root cause. `./index.md`
        keeps a leading `.` segment that the DEFAULT `.*` exclusion matches, so
        the audit emitted a false `techdocs_nav_target_excluded` at its top
        severity rank against a tree a strict build accepts. And a `./`-padded
        entry long enough to trip the subject bound stat-ed True, so the
        existence check passed, and then the bound short-circuited `excluded()`
        to False and erased a real finding.
        """
        text = (self.root / "mkdocs.yml").read_text(encoding="utf-8")
        _page(self.root / "docs" / "agents" / "hidden.md", "Hidden")

        def nav_codes(entry: str) -> list:
            head = text.partition("nav:\n")[0]
            body = (head + "nav:\n  - Only: " + entry + "\nexclude_docs:"
                    + text.split("exclude_docs:", 1)[1])
            (self.root / "mkdocs.yml").write_text(body, encoding="utf-8")
            return [f.code for f in audit.audit_techdocs(self.root).findings
                    if f.code.startswith("techdocs_nav")]

        # Published either way: the `./` is normalization, not a dotfile.
        self.assertEqual(nav_codes("index.md"), [])
        self.assertEqual(nav_codes("./index.md"), [],
                         "`./` is normalized away by MkDocs; the default `.*` exclusion "
                         "must not see a leading dot segment")
        self.assertEqual(nav_codes("././index.md"), [])
        # Genuinely excluded either way: the golden block removes agents/.
        self.assertEqual(nav_codes("agents/hidden.md"), ["techdocs_nav_target_excluded"])
        self.assertEqual(nav_codes("./agents/hidden.md"), ["techdocs_nav_target_excluded"])
        # Long enough to trip the subject bound, but it stats to a real file, so
        # the finding must survive rather than being erased.
        padded = ("./" * 2100) + "agents/hidden.md"
        self.assertGreater(len(padded), audit._MAX_SUBJECT_CHARS)
        self.assertEqual(nav_codes(padded), ["techdocs_nav_target_excluded"])

    def test_an_unstattable_nav_entry_is_a_finding_not_an_error(self):
        """ENAMETOOLONG is not in CPython's ignored-error set for `is_file`.

        One nav entry with an over-long component therefore raised out of the
        nav loop and turned the whole audit into an error envelope, losing every
        other finding in the report. Unstattable is exactly "no file here".
        """
        text = (self.root / "mkdocs.yml").read_text(encoding="utf-8")
        head = text.partition("nav:\n")[0]
        long_entry = "n" * 400 + ".md"
        (self.root / "mkdocs.yml").write_text(
            head + "nav:\n  - Only: " + long_entry + "\nexclude_docs:"
            + text.split("exclude_docs:", 1)[1], encoding="utf-8")
        report = audit.audit_techdocs(self.root)   # must not raise
        codes = [f.code for f in report.findings if f.code.startswith("techdocs_nav")]
        self.assertEqual(codes, ["techdocs_nav_target_missing"])
        self.assertEqual(report.publication["survivor_count"], 4,
                         "the rest of the report must survive one bad nav entry")

    def test_a_pattern_carrying_significant_leading_whitespace_degrades(self):
        """gitignore strips TRAILING whitespace, not leading; the parser stripped both.

        A block scalar's first content line fixes the indentation, so a deeper
        line carries literal leading spaces in the value. Measured against
        PyYAML plus pathspec on a config MkDocs loads without complaint, the
        divergence ran in BOTH directions: this module published ` x.md` where
        MkDocs hides it, and hid `x.md` where MkDocs publishes it. The uniform
        indentation every real config uses is unaffected, which is why the
        randomized corpus never reached this.
        """
        text = ("site_name: Example Documentation\ndocs_dir: docs\n"
                "exclude_docs: |\n  /prompts/*\n   x.md\n")
        (self.root / "mkdocs.yml").write_text(text, encoding="utf-8")
        parsed = audit.parse_mkdocs(text)
        self.assertFalse(parsed["shape_ok"])
        self.assertIn(audit.DEGRADE_MKDOCS_SHAPE, audit.audit_techdocs(self.root).degraded)

        # The rule is symmetric. A LESS indented continuation ends the block
        # scalar, which makes the whole document a YAML parse error, so MkDocs
        # cannot build the site at all; reading a boundary out of a file that
        # does not load is the same silent approximation from the other side.
        less = ("site_name: Example Documentation\ndocs_dir: docs\n"
                "exclude_docs: |\n    /prompts/*\n  x.md\n")
        self.assertFalse(audit.parse_mkdocs(less)["shape_ok"])
        (self.root / "mkdocs.yml").write_text(less, encoding="utf-8")
        self.assertIn(audit.DEGRADE_MKDOCS_SHAPE, audit.audit_techdocs(self.root).degraded)

        # Negative control: the same two patterns at a UNIFORM indent are an
        # ordinary block and must not degrade, or the assertions above are just
        # "any two-line block degrades".
        uniform = ("site_name: Example Documentation\ndocs_dir: docs\n"
                   "exclude_docs: |\n  /prompts/*\n  x.md\n")
        self.assertTrue(audit.parse_mkdocs(uniform)["shape_ok"])
        (self.root / "mkdocs.yml").write_text(uniform, encoding="utf-8")
        self.assertNotIn(audit.DEGRADE_MKDOCS_SHAPE,
                         audit.audit_techdocs(self.root).degraded)

    def test_significant_leading_whitespace_in_quoted_patterns_is_refused(self):
        """DEL-12: inline and sequence quotes preserve their leading space."""
        (self.root / "docs" / "x.md").write_text("# Plain\n", encoding="utf-8")
        (self.root / "docs" / " x.md").write_text("# Spaced\n", encoding="utf-8")
        prefix = "site_name: Example Documentation\ndocs_dir: docs\n"
        for carrier in ("exclude_docs: ' x.md'\n",
                        "exclude_docs:\n  - ' x.md'\n"):
            with self.subTest(carrier=carrier):
                text = prefix + carrier
                parsed = audit.parse_mkdocs(text)
                self.assertTrue(parsed["shape_ok"])
                self.assertEqual(parsed["exclude_docs"], [" x.md"])
                self.assertEqual(audit.unsupported_patterns(parsed["exclude_docs"]), [" x.md"])

                (self.root / "mkdocs.yml").write_text(text, encoding="utf-8")
                report = audit.audit_techdocs(self.root)
                self.assertIn(audit.DEGRADE_MKDOCS_SHAPE, report.degraded)
                self.assertIn("x.md", report.publication["survivor_pages"])
                self.assertIn(" x.md", report.publication["survivor_pages"])

    def test_a_refused_pattern_is_named_not_just_counted(self):
        """`mkdocs_shape` is shared with six conditions and names nothing.

        Refusal became a primary mechanism in this change, so an operator with a
        long `exclude_docs` block would otherwise have to bisect their own
        config to learn which line was dropped.
        """
        text = (self.root / "mkdocs.yml").read_text(encoding="utf-8")
        (self.root / "mkdocs.yml").write_text(
            text.rstrip("\n") + "\n  //bad\n  [z-a].md\n  a\\/b\n", encoding="utf-8")
        report = audit.audit_techdocs(self.root)
        self.assertIn(audit.DEGRADE_MKDOCS_SHAPE, report.degraded)
        self.assertEqual(
            report.publication["unsupported_patterns"],
            ["//bad", "[z-a].md", r"a\/b"],
        )
        # The surviving patterns still compute a boundary, so the field reports
        # what was dropped rather than replacing the answer.
        self.assertIn("index.md", report.publication["survivor_pages"])
        # Absent when nothing was refused, so its presence is meaningful.
        (self.root / "mkdocs.yml").write_text(text, encoding="utf-8")
        clean = audit.audit_techdocs(self.root)
        self.assertNotIn("unsupported_patterns", clean.publication)
        self.assertNotIn(audit.DEGRADE_MKDOCS_SHAPE, clean.degraded)

    def test_a_draft_docs_block_degrades_the_run(self):
        """The PARSE half was pinned and the EMISSION half was not.

        Deleting the degrade from `audit_techdocs` left the whole file green
        while a config carrying `draft_docs` reported clean, which is the exact
        fail-open the degrade exists to prevent: MkDocs omits those pages from
        the build and the audit lists them as published.
        """
        text = (self.root / "mkdocs.yml").read_text(encoding="utf-8")
        (self.root / "mkdocs.yml").write_text(
            text + "draft_docs: |\n  internal/\n", encoding="utf-8")
        report = audit.audit_techdocs(self.root)
        self.assertIn(audit.DEGRADE_DRAFT_DOCS_PRESENT, report.degraded)
        self.assertNotEqual(report.summary["verdict"], audit.VERDICT_CLEAN,
                            "a boundary the audit does not model must never read as clean")
        # Negative control: without the block the same tree does not degrade for
        # this reason, so the assertion above is about `draft_docs` and not about
        # some unrelated property of the fixture.
        (self.root / "mkdocs.yml").write_text(text, encoding="utf-8")
        self.assertNotIn(audit.DEGRADE_DRAFT_DOCS_PRESENT,
                         audit.audit_techdocs(self.root).degraded)

    def test_the_walk_never_descends_outside_the_root(self):
        """AC-3 says the walk must REFUSE TO DESCEND, and no test could see descent.

        Every test that looked at the escaping-symlink case asserted only on the
        returned survivor list, which the surviving per-FILE guard still filters,
        so deleting the per-DIRECTORY guard left them all green while the walk
        readdir'd two directories outside the repository root. The claim is about
        traversal, so the spy has to be on traversal: this is the walk-level
        analogue of the `Path.open` spy the unread-sentinel case already uses.
        """
        if not hasattr(os, "symlink"):  # pragma: no cover
            self.skipTest("symlinks unavailable")
        outside = Path(self.tmp.name) / "beyond"
        (outside / "deep").mkdir(parents=True)
        _page(outside / "leaked.md", "Leaked")
        _page(outside / "deep" / "deeper.md", "Deeper")
        docs = self.root / "docs"
        try:
            os.symlink(outside, docs / "references" / "linked")
        except OSError:  # pragma: no cover
            self.skipTest("symlink creation not permitted")

        resolved_root = os.path.realpath(str(self.root))
        seen: list[str] = []
        real_walk = os.walk

        def spy(top, *args, **kwargs):
            for parent, dirs, files in real_walk(top, *args, **kwargs):
                seen.append(os.path.realpath(parent))
                yield parent, dirs, files

        with unittest.mock.patch.object(os, "walk", spy):
            survivors = audit.survivor_pages(self.root, docs, [])

        outside_root = [p for p in seen
                        if p != resolved_root and not p.startswith(resolved_root + os.sep)]
        self.assertEqual(outside_root, [],
                         "the walk entered a directory outside the repository root")
        self.assertFalse([p for p in survivors if "linked/" in p])
        # The spy must be able to record a violation, or the assertion above is
        # vacuous: the same walk over the escaping tree directly does record one.
        seen.clear()
        with unittest.mock.patch.object(os, "walk", spy):
            list(os.walk(str(outside)))
        self.assertTrue([p for p in seen
                         if p != resolved_root and not p.startswith(resolved_root + os.sep)],
                        "the spy cannot observe an outside-root traversal at all")

    def test_the_two_boundary_details_name_which_side_the_target_is_on(self):
        """One finding code, two causes, and only the detail tells them apart.

        Forcing the `inside_docs` branch true changed neither code, path, href
        nor verdict -- only the detail prose -- and nothing asserted the prose,
        so the mutant survived. That distinction is what AC-8's recorded
        disposition rests on: one dogfood occurrence is a target outside
        `docs_dir` that cannot be moved, the other is a target inside it that
        `exclude_docs` deliberately keeps unpublished.
        """
        docs = self.root / "docs"
        # Under `references/`, which the golden block re-includes, so the linking
        # page is a real survivor and its links are actually walked.
        _page(docs / "references" / "hidden.md", "Hidden")
        _page(docs / "references" / "linker.md", "Linker",
              "[out](../../README.md)\n\n[excluded](hidden.md)\n")
        text = (self.root / "mkdocs.yml").read_text(encoding="utf-8")
        (self.root / "mkdocs.yml").write_text(
            text.rstrip("\n") + "\n  /references/hidden.md\n", encoding="utf-8")
        (self.root / "README.md").write_text("# Readme\n", encoding="utf-8")

        report = audit.audit_techdocs(self.root)
        self.assertIn("references/linker.md", report.publication["survivor_pages"],
                      "the linking page must be published, or no link is walked")
        details = {f.href: f.detail for f in report.findings
                   if f.code == "techdocs_link_outside_boundary"
                   and f.path == "references/linker.md"}
        self.assertEqual(
            details.get("../../README.md"),
            "the target lies outside docs_dir, so it is never a site page")
        self.assertEqual(
            details.get("hidden.md"),
            "exclude_docs removes references/hidden.md from the built site, "
            "so this link 404s there",
            "the excluded case names the RESOLVED docs_dir-relative target; the "
            "outside case has no in-site path to name, which is the asymmetry "
            "Requirement 3 describes")

    def test_a_symlinked_subdirectory_leaving_the_root_is_not_followed(self):
        """Containment refuses it: the walk follows in-root symlinked directories."""
        if not hasattr(os, "symlink"):  # pragma: no cover
            self.skipTest("symlinks unavailable")
        outside = Path(self.tmp.name) / "outside_dir"
        outside.mkdir()
        (outside / "leaked.md").write_text("# Leaked\n" + META, encoding="utf-8")
        try:
            os.symlink(outside, self.root / "docs" / "references" / "linked")
        except OSError:  # pragma: no cover
            self.skipTest("symlink creation not permitted")
        index = self.root / "docs" / "index.md"
        index.write_text(index.read_text(encoding="utf-8")
                         + "\n[Exact directory](references/linked)\n"
                         + "[Skipped directory](references/linked/)\n"
                         + "[Descendant](references/linked/leaked.md)\n",
                         encoding="utf-8")
        self.assertEqual(audit.page_links("[Skipped](references/linked/)"), [],
                         "directory hrefs with a trailing slash remain intentionally skipped")
        report = audit.run_techdocs_audit(self.root, timeout_seconds=2)
        self.assertNotIn("references/linked/leaked.md", report.publication["survivor_pages"])
        self.assertEqual(report.publication["survivor_count"], 4)
        self.assertEqual(report.publication["unsafe_survivor_targets"],
                         ["references/linked/"])
        hrefs = {finding.href for finding in report.findings
                if finding.code == "techdocs_link_outside_boundary"}
        self.assertIn("references/linked", hrefs,
                      "the unsafe directory node must match after href normalization")
        self.assertIn("references/linked/leaked.md", hrefs,
                      "descendants of the unsafe directory remain covered")
        self.assertNotIn("references/linked/", hrefs,
                         "the extraction policy skips trailing-slash directory hrefs")


class TechdocsAuditAudienceTests(unittest.TestCase):
    """AC-4: the audience invariant, and an honest account of when it means anything.

    The plan once claimed a default baseline of "the last commit that touched the
    file, not HEAD". Three readiness lanes falsified that: the last commit to touch
    a path is by construction the commit whose blob for that path equals HEAD's, so
    the two are byte-identical in every repository state. The default is HEAD
    content, the check is informative only against an UNCOMMITTED edit, and the
    clean-tree case is reported as `baseline_identical` plus a degrade rather than
    as a pass. These tests pin that, so the vacuity cannot be reintroduced.
    """

    def setUp(self):
        if shutil.which("git") is None:  # pragma: no cover
            self.skipTest("git unavailable")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "repo"
        self.root.mkdir()
        _build(self.root)
        self._git("init", "-q", ".")
        self._git("config", "user.email", "test@example.invalid")
        self._git("config", "user.name", "Test")
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "baseline")

    def _git(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(self.root), *args], check=True, capture_output=True, text=True)

    def _overview(self) -> Path:
        return self.root / "docs" / "references" / "project-overview.md"

    def test_clean_tree_is_reported_as_not_informative_rather_than_passing(self):
        report = audit.audit_techdocs(self.root)
        entry = report.audience["docs/references/project-overview.md"]
        self.assertTrue(entry["baseline_identical"])
        self.assertIn(audit.DEGRADE_AUDIENCE_NOT_INFORMATIVE, report.degraded)
        # And a degraded run never reports clean.
        self.assertNotEqual(report.summary["verdict"], audit.VERDICT_CLEAN)

    def test_added_headings_pass_and_a_removed_heading_is_a_finding(self):
        path = self._overview()
        original = path.read_text(encoding="utf-8")
        path.write_text(original + "\n## Added section\n", encoding="utf-8")
        report = audit.audit_techdocs(self.root)
        entry = report.audience["docs/references/project-overview.md"]
        self.assertTrue(entry["checked"])
        self.assertFalse(entry["baseline_identical"])
        self.assertTrue(entry["preserved"])

        path.write_text(original + "\n## Added\n", encoding="utf-8")
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "add heading")
        path.write_text(original.replace("# Project overview", "# Renamed"), encoding="utf-8")
        report = audit.audit_techdocs(self.root)
        lost = [f for f in report.findings if f.code == "techdocs_audience_heading_lost"]
        self.assertEqual([f.path for f in lost], ["docs/references/project-overview.md"])
        self.assertEqual(lost[0].severity, audit.SEVERITY_HIGH)
        self.assertIn("# Project overview", report.audience[lost[0].path]["missing_headings"])

    def test_reordered_headings_are_a_finding(self):
        path = self._overview()
        path.write_text("# Project overview\n\n" + META + "\n## Alpha\n\n## Beta\n", encoding="utf-8")
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "two sections")
        path.write_text("# Project overview\n\n" + META + "\n## Beta\n\n## Alpha\n", encoding="utf-8")
        report = audit.audit_techdocs(self.root)
        self.assertIn("techdocs_audience_heading_lost", [f.code for f in report.findings])

    def test_untracked_file_is_named_rather_than_passed_or_crashing(self):
        """A page that was NEVER committed, which is the state a freshly generated docs
        page is in and the one where a last-commit lookup returns an empty ref that must
        never reach git. Distinct from `baseline_missing`, which means tracked in history
        but absent at the resolved ref."""
        other = Path(self.tmp.name) / "fresh"
        other.mkdir()
        _build(other)
        subprocess.run(["git", "init", "-q", str(other)], check=True, capture_output=True)
        for args in (("config", "user.email", "t@example.invalid"), ("config", "user.name", "T")):
            subprocess.run(["git", "-C", str(other), *args], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(other), "add", "docs/ARCHITECTURE.md"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(other), "commit", "-q", "-m", "partial"], check=True, capture_output=True)

        report = audit.audit_techdocs(other)
        entry = report.audience["docs/references/project-overview.md"]
        self.assertFalse(entry["checked"])
        self.assertEqual(entry["degrade"], audit.DEGRADE_BASELINE_UNTRACKED)
        self.assertIn(audit.DEGRADE_BASELINE_UNTRACKED, report.degraded)

    def test_tracked_then_deleted_at_the_ref_is_baseline_missing_not_untracked(self):
        """The other side of the distinction, so the two states cannot be collapsed."""
        self._git("rm", "-q", "docs/references/project-overview.md")
        self._git("commit", "-q", "-m", "delete")
        _page(self._overview(), "Project overview")
        report = audit.audit_techdocs(self.root)
        entry = report.audience["docs/references/project-overview.md"]
        self.assertFalse(entry["checked"])
        self.assertEqual(entry["degrade"], audit.DEGRADE_BASELINE_MISSING)

    def test_absent_from_the_working_tree_is_its_own_state(self):
        self._overview().unlink()
        report = audit.audit_techdocs(self.root)
        entry = report.audience["docs/references/project-overview.md"]
        self.assertFalse(entry["checked"])
        self.assertEqual(entry["degrade"], audit.DEGRADE_WORKING_TREE_MISSING)

    def test_outside_a_git_work_tree_degrades(self):
        shutil.rmtree(self.root / ".git")
        report = audit.audit_techdocs(self.root)
        entry = report.audience["docs/references/project-overview.md"]
        self.assertFalse(entry["checked"])
        self.assertEqual(entry["degrade"], audit.DEGRADE_GIT_UNAVAILABLE)

    def test_a_compare_to_that_looks_like_an_option_is_refused(self):
        report = audit.audit_techdocs(self.root, compare_to="--upload-pack=touch /tmp/pwn")
        self.assertIn(audit.DEGRADE_COMPARE_TO_REFUSED, report.degraded)
        self.assertFalse(report.audience["docs/ARCHITECTURE.md"]["checked"])

    def test_a_ref_carrying_a_newline_is_refused_like_a_leading_dash(self):
        """A leading dash was not the only shape that reaches git's parser.

        `HEAD\n--help` passed a startswith check, and with a genuine heading
        loss planted it turned a real finding into a clean verdict at exit 0 --
        a suppressed finding, not merely a lost degrade.
        """
        for hostile in ("HEAD\n--help", "HEAD\r--help", "\n--upload-pack=x",
                        "HEAD\x00--help", "HEAD\t--help", "HEAD\x1b[A", "HEAD\x7f",
                        "\udcff"):
            with self.subTest(ref=hostile):
                report = audit.audit_techdocs(self.root, compare_to=hostile)
                self.assertIn(audit.DEGRADE_COMPARE_TO_REFUSED, report.degraded)
                self.assertNotEqual(report.summary["verdict"], audit.VERDICT_CLEAN)
                # The degrade token alone did not catch NUL: git truncated the
                # spec, no headings parsed, and the empty sequence trivially
                # satisfied the subsequence check, so the report claimed the
                # headings were preserved over a real loss. Assert the CLAIM,
                # not just the token.
                for entry in report.audience.values():
                    self.assertIsNot(entry.get("preserved"), True)
                    self.assertFalse(entry.get("checked"))
        # Ordinary revision syntax must still be accepted.
        for benign in ("HEAD~1", "HEAD^"):
            with self.subTest(ref=benign):
                report = audit.audit_techdocs(self.root, compare_to=benign)
                self.assertNotIn(audit.DEGRADE_COMPARE_TO_REFUSED, report.degraded)

    def test_the_refused_ref_never_reaches_a_git_argv(self):
        """AC-4's real claim: refused BEFORE any argv is built.

        The degrade token alone does not pin this. A variant that emits the
        token and still passes the attacker-controlled ref to git satisfies the
        token assertion exactly, so the refusal is asserted against the argv the
        sanctioned wrapper is actually called with.
        """
        import index_state_store

        hostile = "--upload-pack=touch /tmp/pwn"
        seen: list[list[str]] = []
        real_run = index_state_store._run_git

        def spy(argv, *args, **kwargs):  # noqa: ANN001
            seen.append(list(argv))
            return real_run(argv, *args, **kwargs)

        index_state_store._run_git = spy  # type: ignore[assignment]
        try:
            report = audit.audit_techdocs(self.root, compare_to=hostile)
        finally:
            index_state_store._run_git = real_run  # type: ignore[assignment]

        self.assertIn(audit.DEGRADE_COMPARE_TO_REFUSED, report.degraded)
        flat = [token for argv in seen for token in argv]
        self.assertNotIn(hostile, flat)
        self.assertFalse([t for t in flat if t.startswith("--upload-pack")])
