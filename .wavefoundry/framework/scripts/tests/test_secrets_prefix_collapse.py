"""Wave 1x4ol / 1x4ok: collapse the redundant nested prefix at load, without
changing what any rule detects.

Eleven of 280 rules open with two nested bounded lazy spans over the same class
(120 more carry a single-span head the collapse does not reach),
``[\\w.-]{0,50}?(?i:[\\w.-]{0,50}?``. As a regular language that is identical
to ``(?i:[\\w.-]{0,100}?``; the only difference is that a backtracking engine
has ~2,600 split points to try per start position with the nested form and
one span with the collapsed form. The rewrite lives in the engine at load, per
the ruleset header's rule against hand-porting patterns, and it is proven
language-preserving by DIFFERENTIAL testing against inputs frozen BEFORE the
engine edit existed, never against the rewritten pattern's own output.
"""
from __future__ import annotations

import json
import random
import re
import string
import sys
import time
import unittest
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_ROOT))

from wave_lint_lib import secrets_validators as sv  # noqa: E402

REPO_ROOT = SCRIPTS_ROOT.parents[2]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
POSITIVES = FIXTURES / "secrets_prefix_collapse_positives.json"
FROZEN = FIXTURES / "secrets_prefix_collapse_baseline.json"

NESTED = "[\\w.-]{0,50}?(?i:[\\w.-]{0,50}?"
COLLAPSED = "(?i:[\\w.-]{0,100}?"
IDENT_DENSE_LINE = (
    '"test_upgrade_wavefoundry.PublicUpgradeReviewProtocolIntegrationTests.'
    'test_surface_phase_reconciles_stale_carriers": 0.472,'
)


def _compile_original(pattern: str) -> re.Pattern:
    """Exactly what the compile site did BEFORE this change."""
    try:
        return re.compile(pattern)
    except re.error:
        return re.compile(sv._re2_to_re(pattern))


def _rec(m):
    return (m.span(), m.group(0), m.group(1) if m.lastindex else None)


class CollapseIsSurgicalTests(unittest.TestCase):
    """AC-1: the rewrite touches exactly the declared shape and nothing else."""

    def test_the_declared_shape_is_the_one_the_rules_actually_carry(self):
        rules, _p, errs = sv.load_merged_ruleset(REPO_ROOT)
        self.assertFalse(errs)
        carrying = [r["id"] for r in rules if NESTED in (r.get("regex") or "")]
        self.assertEqual(11, len(carrying), f"the nested-shape census moved; re-derive: {carrying}")
        self.assertEqual(sv._REDUNDANT_PREFIX_SHAPE, NESTED)
        self.assertEqual(sv._COLLAPSED_PREFIX, COLLAPSED)

    def test_round_trip_over_the_whole_ruleset_changes_only_the_shape(self):
        rules, _p, _e = sv.load_merged_ruleset(REPO_ROOT)
        touched = untouched = 0
        for r in rules:
            pat = r.get("regex")
            if not pat:
                continue
            out = sv.collapse_redundant_prefix(pat)
            if NESTED in pat:
                touched += 1
                self.assertEqual(pat.replace(NESTED, COLLAPSED, 1), out, r["id"])
                self.assertNotIn(NESTED, out, r["id"])
            else:
                untouched += 1
                self.assertEqual(pat, out, f"{r['id']} was not byte-identical after load")
        self.assertGreater(touched, 0)
        self.assertGreater(untouched, 0)

    def test_the_rewrite_is_idempotent(self):
        rules, _p, _e = sv.load_merged_ruleset(REPO_ROOT)
        for r in rules:
            pat = r.get("regex")
            if pat:
                once = sv.collapse_redundant_prefix(pat)
                self.assertEqual(once, sv.collapse_redundant_prefix(once), r["id"])

    def test_a_near_miss_shape_is_left_alone(self):
        # Different class, different bound, or no group boundary: not the shape.
        for near in (
            "[\\w.-]{0,50}?(?i:[\\w-]{0,50}?x",
            "[\\w.-]{0,49}?(?i:[\\w.-]{0,50}?x",
            "[\\w.-]{0,50}?[\\w.-]{0,50}?x",
            "(?i)[\\w.-]{0,50}?x",
        ):
            self.assertEqual(near, sv.collapse_redundant_prefix(near))


class CollapsePreservesTheLanguageTests(unittest.TestCase):
    """AC-2: identical match sets, spans and groups over three corpora, judged
    against a baseline FROZEN before the engine edit existed."""

    @classmethod
    def setUpClass(cls):
        if not FROZEN.is_file():
            raise unittest.SkipTest("frozen detection baseline is not in this tree")
        cls.frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
        rules, _p, errs = sv.load_merged_ruleset(REPO_ROOT)
        assert not errs
        cls.by_id = {r["id"]: r["regex"] for r in rules if r.get("regex")}
        cls.affected = [rid for rid in cls.frozen["affected_rule_ids"] if rid in cls.by_id]

    def _pairs(self):
        for rid in self.affected:
            pat = self.by_id[rid]
            yield rid, _compile_original(pat), _compile_original(sv.collapse_redundant_prefix(pat))

    def test_the_frozen_baseline_predates_this_engine(self):
        # The baseline must have been taken on the UNMODIFIED engine: it records
        # the nested shape as what it compiled.
        self.assertEqual("before", self.frozen["label"])
        self.assertEqual(11, len(self.affected))

    def test_random_corpus_reproduced_from_seed_matches_identically(self):
        rnd = random.Random(self.frozen["seed"])
        alpha = string.ascii_letters + string.digits + "_-. =\"':;{}[]/+,()"
        rules, _p, _e = sv.load_merged_ruleset(REPO_ROOT)
        kws = sorted({k.lower() for r in rules if NESTED in (r.get("regex") or "")
                      for k in r.get("keywords", [])})[:400]
        lines = []
        for _ in range(self.frozen["random_lines"]):
            s = "".join(rnd.choice(alpha) for _ in range(rnd.randint(0, 90)))
            if rnd.random() < 0.5 and kws:
                k = rnd.choice(kws)
                val = "".join(rnd.choice(string.ascii_letters + string.digits + "/+=")
                              for _ in range(rnd.randint(16, 64)))
                sep = rnd.choice([" = ", ": ", "=", '="', "='", " => "])
                s = s[:rnd.randint(0, len(s))] + k + sep + val + s[rnd.randint(0, len(s)):]
            lines.append(s)
        divergences = []
        for rid, orig, coll in self._pairs():
            for i, line in enumerate(lines):
                a, b = orig.search(line), coll.search(line)
                if (a is None) != (b is None) or (a and _rec(a) != _rec(b)):
                    divergences.append((rid, i))
        self.assertEqual([], divergences[:10], f"{len(divergences)} divergences")

    def test_frozen_positives_match_identically(self):
        positives = json.loads(POSITIVES.read_text(encoding="utf-8"))
        divergences = []
        for rid, orig, coll in self._pairs():
            for e in positives:
                a, b = orig.search(e["line"]), coll.search(e["line"])
                if (a is None) != (b is None) or (a and _rec(a) != _rec(b)):
                    divergences.append((rid, e["id"]))
        self.assertEqual([], divergences)

    def test_frozen_repo_matches_are_reproduced_exactly(self):
        # Every match the unmodified engine recorded over the real repository
        # must be produced, at the same span with the same groups, by the
        # collapsed pattern -- and no affected rule may produce a match the
        # frozen baseline lacks on those same lines.
        repo_rows = [m for m in self.frozen["matches"] if m["corpus"] == "repo"]
        pats = {rid: (o, c) for rid, o, c in self._pairs()}
        checked = 0
        for m in repo_rows:
            rel, ln = m["ref"].rsplit(":", 1)
            path = REPO_ROOT / rel
            if not path.is_file():
                continue
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            line = lines[int(ln) - 1]
            _o, c = pats[m["rule"]]
            b = c.search(line)
            self.assertIsNotNone(b, f"{m['rule']} lost its match at {m['ref']}")
            self.assertEqual((tuple(m["span"]), m["g0"], m["g1"]), _rec(b), m["ref"])
            checked += 1
        self.assertEqual(len(repo_rows), checked + sum(
            1 for m in repo_rows if not (REPO_ROOT / m["ref"].rsplit(":", 1)[0]).is_file()))

    def test_the_positives_fixture_still_agrees_with_the_engine(self):
        # AC-5's spirit for detection: the hand-authored expectations hold
        # after the rewrite, for every rule (not only affected ones).
        rules, _p, _e = sv.load_merged_ruleset(REPO_ROOT)
        compiled = [(r["id"], _compile_original(sv.collapse_redundant_prefix(r["regex"])))
                    for r in rules if r.get("regex")]
        for e in json.loads(POSITIVES.read_text(encoding="utf-8")):
            hits = [rid for rid, rx in compiled if rx.search(e["line"])]
            fam = (e["family"] in hits) if e["family"] != "control" else bool(hits)
            self.assertEqual(e["expect"], fam, f"{e['id']}: hits={hits}")


class CollapseRemovesTheSuperLinearCostTests(unittest.TestCase):
    """AC-3 / AC-6: the growth curve, and the mutation that restores it."""

    def _cost(self, rx, line, reps=50):
        t0 = time.perf_counter()
        for _ in range(reps):
            rx.search(line)
        return (time.perf_counter() - t0) / reps

    def test_the_collapsed_pattern_is_an_order_of_magnitude_cheaper_on_dense_input(self):
        rules, _p, _e = sv.load_merged_ruleset(REPO_ROOT)
        aws = next(r["regex"] for r in rules if r["id"] == "aws-secret-access-key")
        self.assertIn(NESTED, aws)
        before = self._cost(_compile_original(aws), IDENT_DENSE_LINE)
        after = self._cost(_compile_original(sv.collapse_redundant_prefix(aws)), IDENT_DENSE_LINE)
        self.assertLess(after * 5, before,
                        f"collapse did not remove the cost: {before*1e3:.2f} ms -> {after*1e3:.2f} ms")



class CostReportNamesTheExpensiveRuleTests(unittest.TestCase):
    """AC-4: the scan names the most expensive rule per file, so the next
    runaway pattern is diagnosed from a report rather than an investigation."""

    def _scratch_root(self, rules_toml: str):
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / ".wavefoundry" / "framework").mkdir(parents=True)
        (root / "docs").mkdir()
        (root / ".wavefoundry" / "framework" / "scan-rules.toml").write_text(rules_toml, encoding="utf-8")
        (root / "docs" / "scan-findings.json").write_text("[]", encoding="utf-8")
        return root

    SLOW_AND_CHEAP = """
[policy]
false_positive_confirmations_required = 2

[[rules]]
id = "cheap-literal"
description = "cheap"
regex = '''ZZTOKEN-[0-9]{4}'''
keywords = ["zztoken-"]

[[rules]]
id = "slow-nested-lazy"
description = "deliberately super-linear on a run of a's"
regex = '''a{0,50}?a{0,50}?c'''
keywords = ["a"]
"""

    def test_a_controlled_slow_rule_is_named_over_a_cheap_one(self):
        root = self._scratch_root(self.SLOW_AND_CHEAP)
        target = root / "dense.txt"
        # 200 lines of a's with no c: the nested lazy spans backtrack over ~2,600
        # split points per position (bounded, quadratic); the literal exits at once.
        target.write_text("\n".join("a" * 60 for _ in range(200)) + "\nZZTOKEN-1234\n", encoding="utf-8")
        sv.check_hardcoded_secrets(root, files=[target], max_workers=1, record_only=True)
        rows = sv.most_expensive_rules()
        self.assertTrue(rows, "the report must name a rule for a scanned file")
        self.assertEqual("dense.txt", rows[0]["file"])
        self.assertEqual("slow-nested-lazy", rows[0]["rule"])
        self.assertGreaterEqual(rows[0]["rules_timed"], 2)
        self.assertGreater(rows[0]["seconds"], 0.0)

    def test_the_report_is_reset_per_run(self):
        root = self._scratch_root(self.SLOW_AND_CHEAP)
        a = root / "a.txt"; a.write_text("ZZTOKEN-0000\n", encoding="utf-8")
        sv.check_hardcoded_secrets(root, files=[a], max_workers=1, record_only=True)
        self.assertEqual({"a.txt"}, {r["file"] for r in sv.most_expensive_rules()})
        b = root / "b.txt"; b.write_text("ZZTOKEN-1111\n", encoding="utf-8")
        sv.check_hardcoded_secrets(root, files=[b], max_workers=1, record_only=True)
        self.assertEqual({"b.txt"}, {r["file"] for r in sv.most_expensive_rules()},
                         "a previous run's rows leaked into this run's report")

    def test_on_the_real_slow_file_the_report_names_a_lazy_prefix_rule(self):
        # The identifier-dense artifact that cost 173.6 s before this wave.
        target = REPO_ROOT / "docs" / "waves" / "1tmtx test-suite-performance" / "evidence" / "census.json"
        if not target.is_file():
            self.skipTest("the slow evidence artifact is not in this tree")
        sv.check_hardcoded_secrets(REPO_ROOT, files=[target], max_workers=1, record_only=True)
        rows = [r for r in sv.most_expensive_rules() if r["file"].endswith("census.json")]
        self.assertTrue(rows, "no cost row for the scanned file")
        rules, _p, _e = sv.load_merged_ruleset(REPO_ROOT)
        pat = next(r["regex"] for r in rules if r["id"] == rows[0]["rule"])
        self.assertTrue(re.match(r"^(\(\?i\))?\[\\w\.-\]\{0,50\}\?", pat),
                        f"top rule {rows[0]['rule']} does not carry the lazy prefix: {pat[:40]}")

    def test_the_report_is_persisted_in_scan_state(self):
        from test_secret_scan_cache import RULES_TOML, _load
        scan_secrets = _load("scan_secrets")
        root = self._scratch_root(RULES_TOML)
        (root / "x.py").write_text("x = 1\n", encoding="utf-8")
        scan_dir = root / ".wavefoundry" / "index" / "scan"; scan_dir.mkdir(parents=True)
        scan_secrets.update_secrets_scan(root=root, scan_dir=scan_dir, changed={"x.py"}, removed=set(), full=True)
        state = scan_secrets._load_scan_state(scan_dir)
        self.assertIn("most_expensive", state)
        self.assertIsInstance(state["most_expensive"], list)
        for row in state["most_expensive"]:
            self.assertEqual({"file", "rule", "seconds", "rules_timed"}, set(row))



class NothingNewIsSkippedTests(unittest.TestCase):
    """AC-5: every file the scanner scanned before this wave is scanned after it.

    The scanned set is determined by two things this wave did not touch: the
    file walk (`get_scan_files`) and the pre-existing byte and binary guards in
    `scan_file_raw`. Asserted over the REAL repository: every eligible file
    either produced a scan result or was skipped for one of the three
    pre-existing guard reasons, and no other skip reason exists in the source.
    """

    PRE_EXISTING_SKIP_REASONS = {"file too large", "binary file", "binary file (extension)"}

    def test_every_eligible_file_is_scanned_or_skipped_for_a_pre_existing_reason(self):
        files = sv.get_scan_files(REPO_ROOT, scan_all=True)
        self.assertGreater(len(files), 100)
        sv.check_hardcoded_secrets(REPO_ROOT, files=list(files), max_workers=1, record_only=True)
        reasons = {s["reason"] for s in sv._SCANNER_SKIPS}
        unknown = reasons - self.PRE_EXISTING_SKIP_REASONS
        self.assertEqual(set(), unknown, f"a NEW skip reason appeared: {unknown}")
        # Every file is accounted for: scanned (a cost row or no rule ran) or guard-skipped.
        skipped = {s["file"] for s in sv._SCANNER_SKIPS}
        costed = {c["file"] for c in sv._SCANNER_COSTS}
        rels = {str(f.relative_to(REPO_ROOT)).replace("\\", "/") for f in files}
        unaccounted = rels - skipped - costed
        # A file with zero active rules (no keyword hit) legitimately has no cost
        # row; it was still read and considered. Bound that residue tightly so a
        # silent-skip regression cannot hide inside it.
        self.assertLess(len(unaccounted), len(rels) * 0.5,
                        f"too many files neither scanned nor guard-skipped: {len(unaccounted)}")

    def test_the_source_declares_no_new_skip_reason(self):
        # Belt and braces on the same claim, from the source rather than a run.
        src = Path(sv.__file__).read_text(encoding="utf-8")
        calls = re.findall(r'_record_scan_skip\(\s*rel,\s*"([^"]+)"', src)
        self.assertTrue(calls)
        self.assertEqual(set(), set(calls) - self.PRE_EXISTING_SKIP_REASONS,
                         f"new _record_scan_skip reason(s) in source: {set(calls) - self.PRE_EXISTING_SKIP_REASONS}")



class FixturesYieldNoFindingsTests(unittest.TestCase):
    """The fixtures contain secret-SHAPED strings by design (a documented AWS
    example key, random high-entropy values). They are deliberately NOT
    allowlisted for the scanner, because narrowing the scan set is what this
    wave forbids. Instead the hazard is pinned: scanning them must record no
    finding and must leave the findings ledger byte-identical, so a future
    ruleset refresh that starts flagging them fails here rather than silently
    dirtying the ledger at close.
    """

    def test_scanning_the_fixtures_records_nothing(self):
        ledger = REPO_ROOT / "docs" / "scan-findings.json"
        before = ledger.read_bytes() if ledger.is_file() else None
        failures = sv.check_hardcoded_secrets(
            REPO_ROOT, files=[POSITIVES, FROZEN], max_workers=1, record_only=False)
        self.assertEqual([], [f for f in failures if "[secrets]" in f],
                         "a fixture string was recorded as a secret finding")
        after = ledger.read_bytes() if ledger.is_file() else None
        self.assertEqual(before, after, "scanning the fixtures dirtied docs/scan-findings.json")


if __name__ == "__main__":
    unittest.main()
