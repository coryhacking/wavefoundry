"""Containment bootstrap: real filesystem boundaries and identity membership."""

from pathlib import Path, PureWindowsPath
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import path_containment as subject


class ContainedPathTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / "root"
        self.root.mkdir()
        self.outside = self.base / "outside"
        self.outside.mkdir()

    def test_parent_escape_with_missing_tail(self):
        self.assertIsNone(subject.contained_path(self.root, "../outside/missing/leaf"))

    def test_absolute_inside_and_escape(self):
        inside = self.root / "missing"
        self.assertEqual(inside, subject.contained_path(self.root, inside))
        self.assertIsNone(subject.contained_path(self.root, self.outside / "missing"))

    def test_directory_link_escape_with_missing_tail(self):
        (self.root / "link").symlink_to(self.outside, target_is_directory=True)
        self.assertIsNone(subject.contained_path(self.root, "link/missing"))

    def test_file_link_escape(self):
        target = self.outside / "file"
        target.write_text("outside")
        (self.root / "link").symlink_to(target)
        self.assertIsNone(subject.contained_path(self.root, "link"))

    def test_dangling_links_inside_and_outside(self):
        (self.root / "bad").symlink_to(self.outside / "missing")
        (self.root / "good").symlink_to(self.root / "missing")
        self.assertIsNone(subject.contained_path(self.root, "bad"))
        self.assertEqual(self.root / "missing", subject.contained_path(self.root, "good"))
        self.assertIsNone(subject.contained_path(self.root, "good", refuse_symlink_components=True))

    def test_root_itself(self):
        self.assertEqual(self.root, subject.contained_path(self.root, self.root))

    def test_relative_inside(self):
        self.assertEqual(self.root / "nested" / "file", subject.contained_path(self.root, "nested/file"))

    def test_symlink_root_both_spellings(self):
        alias = self.base / "alias"
        alias.symlink_to(self.root, target_is_directory=True)
        for candidate in (alias / "missing", self.root / "missing"):
            for refuse in (False, True):
                self.assertEqual(self.root / "missing", subject.contained_path(
                    alias, candidate, refuse_symlink_components=refuse))

    def test_loop_refused_on_each_interpreter_branch(self):
        loop = self.root / "loop"
        loop.symlink_to(loop)
        # Independent pathlib behavior changed in 3.13; the primitive's
        # uncertainty contract remains stable across both branches.
        if sys.version_info < (3, 13):
            with self.assertRaises(RuntimeError):
                loop.resolve(strict=False)
        else:
            self.assertEqual(loop, loop.resolve(strict=False))
        for strict in (False, True):
            self.assertIsNone(subject.contained_path(self.root, loop, strict=strict))

    def test_leave_and_reenter_link(self):
        (self.outside / "back").symlink_to(self.root, target_is_directory=True)
        (self.root / "exit").symlink_to(self.outside, target_is_directory=True)
        candidate = self.root / "exit" / "back" / "missing"
        self.assertEqual(self.root / "missing", subject.contained_path(self.root, candidate))
        self.assertIsNone(subject.contained_path(self.root, candidate, refuse_symlink_components=True))

    def test_case_only_difference(self):
        # Deliberately compare differently spelled roots without samefile or
        # normcase. This asserts the POSIX predicate even on casefolded disks.
        if sys.platform == "win32":
            self.assertEqual(self.root / "file", subject.contained_path(self.root, self.root / "file"))
        else:
            self.assertIsNone(subject.contained_path(self.root, self.base / "ROOT" / "file"))

    def test_windows_path_pairs_without_posix_normcase(self):
        class ResolvedWindowsPath(PureWindowsPath):
            def resolve(self, strict=False):
                return self

            def stat(self):
                raise FileNotFoundError

        cases = [
            ("C:/repo", "D:/repo/file", False),
            ("C:/repo", "c:/REPO/file", True),
            ("//host/share/repo", "//host/share/repo/file", True),
            ("//host/share/repo", "//host/other/repo/file", False),
            ("C:/repo", "\\\\?\\C:\\repo\\file", False),
        ]
        with patch.object(subject, "Path", ResolvedWindowsPath):
            for root, candidate, accepted in cases:
                with self.subTest(root=root, candidate=candidate):
                    actual = subject.contained_path(root, candidate)
                    self.assertEqual(ResolvedWindowsPath(candidate) if accepted else None, actual)

    def test_strict_missing_candidate(self):
        self.assertIsNone(subject.contained_path(self.root, "missing", strict=True))
        target = self.root / "present"
        target.write_text("inside")
        self.assertEqual(target, subject.contained_path(self.root, target, strict=True))

    def test_resolution_failures_map_to_none(self):
        for error in (OSError("permission"), RuntimeError("loop"), ValueError("invalid")):
            with self.subTest(error=type(error).__name__), patch.object(Path, "resolve", side_effect=error):
                self.assertIsNone(subject.contained_path(self.root, "file"))


class ProductionIdentityTests(unittest.TestCase):
    def test_real_module_edit_changes_identity_independent_of_membership_list(self):
        import retrieval_eval

        with tempfile.TemporaryDirectory() as temp:
            scripts = Path(temp)
            # Copy the target independently of the membership tuple: removing
            # its registration must make the digest assertion fail, not remove
            # the target from the fixture and falsely pass.
            for source in SCRIPTS.glob("*.py"):
                shutil.copyfile(source, scripts / source.name)
            target = scripts / "path_containment.py"
            self.assertTrue(target.is_file())
            before = retrieval_eval._production_identity(scripts)
            target.write_text(target.read_text() + "\n# identity mutation\n")
            after = retrieval_eval._production_identity(scripts)
            self.assertIn("path_containment.py", before["modules"])
            self.assertNotEqual(before["digest"], after["digest"])


class ResolvedComparisonTests(unittest.TestCase):
    def test_pure_helper_performs_no_filesystem_work(self):
        from contextlib import ExitStack
        with ExitStack() as stack:
            for operation in ('resolve', 'stat', 'lstat', 'absolute'):
                stack.enter_context(patch.object(Path, operation, side_effect=AssertionError(operation)))
            root = Path('/repo')
            inside = root / 'missing'
            self.assertIs(inside, subject.contained_resolved_path(root, inside))
            self.assertEqual(root, subject.contained_resolved_path(root, root))
            self.assertIsNone(subject.contained_resolved_path(root, Path('/other')))
            self.assertIsNone(subject.contained_resolved_path(root, Path('/REPO/other')))
            self.assertEqual(PureWindowsPath('c:/REPO/file'), subject.contained_resolved_path(
                PureWindowsPath('C:/repo'), PureWindowsPath('c:/REPO/file')))
            self.assertIsNone(subject.contained_resolved_path(
                PureWindowsPath('//host/share'), PureWindowsPath('//host/other/file')))


class WrapperContractTests(unittest.TestCase):
    def test_renderer_and_techdocs_resolution_matrix(self):
        import render_agent_surfaces as renderer
        import techdocs_audit_lib as techdocs
        root, candidate = Path('/repo'), Path('/repo/missing')
        for wrapper in (renderer._contained_review_carrier_path, techdocs._contained):
            with self.subTest(wrapper=wrapper.__module__, case='extra-resolution-refused'):
                with patch.object(Path, 'resolve', side_effect=[root, candidate, OSError('extra resolve')]) as resolve, patch.object(Path, 'stat', side_effect=AssertionError('extra stat')), patch.object(Path, 'lstat', side_effect=AssertionError('extra lstat')):
                    self.assertEqual(candidate, wrapper(root, 'missing'))
                    self.assertEqual(2, resolve.call_count)
            for location in ('root', 'candidate'):
                for error_type in (OSError, RuntimeError):
                    error = error_type('injected fault')
                    side_effect = error if location == 'root' else [root, error]
                    with self.subTest(wrapper=wrapper.__module__, location=location, error=error_type.__name__), patch.object(Path, 'resolve', side_effect=side_effect):
                        if wrapper is techdocs._contained and (location == 'candidate' or error_type is RuntimeError):
                            self.assertIsNone(wrapper(root, 'missing'))
                        elif location == 'candidate' and error_type is OSError:
                            with self.assertRaisesRegex(RuntimeError, 'review carrier path cannot be resolved safely') as caught:
                                wrapper(root, 'missing')
                            self.assertIs(error, caught.exception.__cause__)
                        else:
                            with self.assertRaises(error_type) as caught:
                                wrapper(root, 'missing')
                            self.assertIs(error, caught.exception)
            with self.subTest(wrapper=wrapper.__module__, case='escape'), patch.object(Path, 'resolve', side_effect=[root, Path('/outside')]):
                if wrapper is techdocs._contained:
                    self.assertIsNone(wrapper(root, 'missing'))
                else:
                    with self.assertRaisesRegex(RuntimeError, 'escapes the repository root through a symlink'):
                        wrapper(root, 'missing')

    def test_missing_write_target_and_previously_uncovered_escapes(self):
        import context_efficiency
        import memory_supply
        import render_agent_surfaces
        import techdocs_audit_lib
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            root = base / 'root'
            root.mkdir()
            outside = base / 'outside.md'
            outside.write_text('outside')
            (root / 'escape.md').symlink_to(outside)
            self.assertIsNone(context_efficiency._contained_prompt(root, Path('escape.md')))
            self.assertFalse(memory_supply._contained_source_file(root, root / 'escape.md'))
            good = root / 'good.md'
            good.write_text('inside')
            self.assertEqual(good, context_efficiency._contained_prompt(root, Path('good.md')))
            self.assertTrue(memory_supply._contained_source_file(root, good))
            for wrapper in (render_agent_surfaces._contained_review_carrier_path, techdocs_audit_lib._contained):
                self.assertEqual(root / 'missing/leaf', wrapper(root, 'missing/leaf'))

    def test_retained_policy_clauses(self):
        import ast
        clauses = {
            ('context_efficiency.py', '_contained_prompt'): ['Path(root).resolve(strict=True)', '(resolved_root / relative).resolve(strict=True)', 'not prompt.is_file()', 'except (OSError, RuntimeError, ValueError)'],
            ('memory_backfill.py', '_contained_source_file'): ['_canonical_waves_dir(root)', 'wave_dir.resolve(strict=True)', 'path.resolve(strict=True)', 'not wave_dir.is_symlink()', 'not path.is_symlink()', 'path.is_file()', 'except (OSError, RuntimeError)'],
            ('memory_supply.py', '_contained_source_file'): ['wave_dir.resolve(strict=True)', 'path.resolve(strict=True)', 'not wave_dir.is_symlink()', 'not path.is_symlink()', 'path.is_file()', 'except (OSError, RuntimeError)'],
            ('memory_records.py', '_contained_record_path'): ['validate_memory_id(memory_id)', 'canonical_memory_root(root)', 'resolved.parent != expected_root', 'return path'],
            ('memory_records.py', '_contained_memory_subdir_path'): ['validate_memory_id(memory_id)', 'subdir not in ("archive", "pointers")', 'canonical_memory_root(root)', 'resolved.parent != expected_parent', 'return path'],
            ('memory_records.py', '_contained_purge_staging_path'): ['validate_memory_id(memory_id)', 'canonical_memory_root(root)', 'resolved.parent != expected_parent', 'return path'],
            ('server_impl.py', '_contained_wave_review_paths'): ['record_paths.load_record_roots(root)', 'waves_root != expected_waves_root', 'wave_dir.relative_to(waves_root).parts', '1 <= len(depth_parts) <= allowed_depth', 'wave_md.resolve(strict=False) != expected_wave_md', 'expected_events.resolve(strict=False) != expected_events', 'from exc'],
            ('server_impl.py', 'resolve_path_under_root'): ['root = repo_root.resolve()', 'raw.resolve() if raw.is_absolute() else (root / raw).resolve()', 'except (OSError, RuntimeError) as exc:', '"path_resolution_failed"', '"path_outside_allowed_roots"'],
            ('review_policy.py', 'contained_relative_path'): ['root.resolve(strict=True)', 'for part in Path(relative).parts:', 'cursor.is_symlink()', 'target.resolve(strict=False)', 'return target'],
        }
        for (filename, name), retained in clauses.items():
            source = (SCRIPTS / filename).read_text()
            node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == name)
            body = ast.get_source_segment(source, node)
            for clause in retained:
                with self.subTest(site=name, clause=clause):
                    self.assertIn(clause, body)
            self.assertIn('contained_resolved_path(', body)


# The scanner is deliberately an approximation; the independent 30-site
# inventory also pins helpers outside it (lexical, lstat-only, or larger policy
# guards). These two equality predicates are identities/traversal, not security
# containment, and remain explicit so the approximation cannot silently grow.
CENSUS_FALSE_POSITIVES = {
    ('venv_bootstrap.py', '_running_inside_venv'): 'Interpreter identity, not path authority.',
    ('build_pack.py', 'find_repo_root'): 'Ancestor traversal termination, not containment.',
}
CONTAINMENT_ALLOWLIST = {
    ('indexer.py', '_is_relative_to'): 'Keep OSError/RuntimeError aborting the prepared-removal veto; follow-up only with a contract review.',
    ('context_efficiency.py', 'contained_stat_signature'): 'FileVersion/stat observation contract; separate follow-up.',
    ('memory_backfill.py', '_canonical_waves_dir'): 'Record-layout directory authority and OSError diagnostics; separate follow-up.',
    ('memory_records.py', 'canonical_memory_root'): 'Exact canonical equality and unresolved return; separate follow-up.',
    ('memory_records.py', '_purge_disposition_path'): 'Disposition authority rejects parent/final symlinks; separate follow-up.',
    ('server_impl.py', '_resolve_repo_path'): 'Absolute-input refusal and selective error mapping; separate follow-up.',
    ('techdocs_audit_lib.py', '_inside'): 'Nested lexical string-prefix predicate; separate follow-up.',
    ('retrieval_eval.py', '_path_under_root'): 'Relative string return, selective errors and evaluator identity; separate follow-up.',
    ('retrieval_eval.py', 'confined_report_path'): 'Report publication filename/role/lstat authority; separate follow-up.',
    ('docs_gardener.py', '_under_a_scan_root'): 'Multiple scan-root policy; separate follow-up.',
    ('dashboard_server.py', '_asset_path'): 'Fixed asset root and FileNotFoundError; separate follow-up.',
    ('setup_readiness.py', '_safe'): 'ObservationError and unresolved return; separate follow-up.',
    ('record_paths.py', '_resolved_inside'): 'Hot-loop realpath contract forbids Path.resolve; separate follow-up.',
    ('lifecycle_gates.py', '_framework_test_receipt_status'): 'Structured receipt proof gate; separate follow-up.',
    ('upgrade_extensions.py', '_guard_owned_path'): 'No-resolve lstat/reparse authority; separate follow-up.',
    ('upgrade_wavefoundry.py', '_retired_sidecar_path_error'): 'Deletion-specific missing/existing policy; separate follow-up.',
    ('review_evidence.py', '_review_authority_path_error'): 'Ledger member rules and path-free diagnostics; separate follow-up.',
    ('wave_lint_lib/helpers.py', '_is_under'): 'Lexical by design; separate follow-up.',
    ('repair_ppol_memory_staging.py', 'safe'): 'Owned-boundary lstat/reparse policy; separate follow-up.',
}
ADOPTED_CONTAINMENT = {
    ('render_agent_surfaces.py', '_contained_review_carrier_path'),
    ('techdocs_audit_lib.py', '_contained'),
    ('context_efficiency.py', '_contained_prompt'),
    ('memory_backfill.py', '_contained_source_file'),
    ('memory_supply.py', '_contained_source_file'),
    ('memory_records.py', '_contained_record_path'),
    ('memory_records.py', '_contained_memory_subdir_path'),
    ('memory_records.py', '_contained_purge_staging_path'),
    ('server_impl.py', '_contained_wave_review_paths'),
    ('server_impl.py', 'resolve_path_under_root'),
    ('review_policy.py', 'contained_relative_path'),
}


def _containment_calls(node):
    import ast
    return {n.func.id if isinstance(n.func, ast.Name) else n.func.attr
            if isinstance(n.func, ast.Attribute) else '?'
            for n in ast.walk(node) if isinstance(n, ast.Call)}


def _containment_candidate(node):
    import ast
    if not isinstance(node, ast.FunctionDef):
        return False
    nodes = list(ast.walk(node))
    calls = _containment_calls(node)
    permitted = {'Path', 'str', 'ValueError', 'OSError', 'RuntimeError',
                 'FileNotFoundError', 'Optional', 'len', 'getattr', '_diagnostic',
                 '_canonical_waves_dir', 'canonical_memory_root', 'validate_memory_id',
                 'load_record_roots', 'ObservationError', 'relative_to', 'is_relative_to',
                 'resolve', 'realpath', 'is_absolute', 'is_file', 'is_dir', 'is_symlink',
                 'exists', 'parts', 'strip', 'expanduser', 'joinpath', 'as_posix',
                 'startswith', 'lstat', 'contained_resolved_path', 'contained_path'}
    return bool(
        calls & {'resolve', 'realpath'}
        and (calls & {'relative_to', 'is_relative_to'} or any(
            isinstance(n, ast.Compare) and any(isinstance(op, (ast.Eq, ast.NotEq)) for op in n.ops)
            for n in nodes))
        and sum(isinstance(n, ast.stmt) for n in nodes) <= 25
        and any(isinstance(n, ast.Raise) or isinstance(n, ast.Return)
                and isinstance(n.value, ast.Constant) for n in nodes)
        and calls <= permitted
    )


def _containment_functions(root):
    import ast
    result = {}
    for path in root.rglob('*.py'):
        if 'tests' in path.relative_to(root).parts or path.name == 'path_containment.py':
            continue
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                result[(path.relative_to(root).as_posix(), node.name)] = node
    return result


def _containment_stale_entries(functions, exemptions):
    return {site for site, reason in exemptions.items()
            if not reason or site not in functions or _containment_calls(functions[site])
            & {'contained_path', 'contained_resolved_path'}}


class ContainmentCensusTests(unittest.TestCase):
    def test_census_and_independent_thirty_site_inventory(self):
        functions = _containment_functions(SCRIPTS)
        self.assertEqual(19, len(CONTAINMENT_ALLOWLIST))
        self.assertEqual(11, len(ADOPTED_CONTAINMENT))
        self.assertFalse(ADOPTED_CONTAINMENT & CONTAINMENT_ALLOWLIST.keys())
        self.assertFalse(_containment_stale_entries(functions, CONTAINMENT_ALLOWLIST))
        self.assertFalse(_containment_stale_entries(functions, CENSUS_FALSE_POSITIVES))
        for site in ADOPTED_CONTAINMENT:
            with self.subTest(site=site):
                self.assertIn(site, functions)
                expected = '_contained_review_carrier_path' if site == ('techdocs_audit_lib.py', '_contained') else 'contained_resolved_path'
                self.assertIn(expected, _containment_calls(functions[site]))
        detected = {site for site, node in functions.items() if _containment_candidate(node)}
        unexplained = detected - ADOPTED_CONTAINMENT - CONTAINMENT_ALLOWLIST.keys() - CENSUS_FALSE_POSITIVES.keys()
        self.assertFalse(unexplained, sorted(unexplained))

    def test_both_new_helper_polarities_are_detected(self):
        snippets = {
            'resolve.py': 'def copied(root, path):\n    try:\n        path.resolve().relative_to(root.resolve())\n        return True\n    except ValueError:\n        return False\n',
            'realpath.py': 'def copied(root, path):\n    try:\n        Path(os.path.realpath(path)).relative_to(os.path.realpath(root))\n        return True\n    except ValueError:\n        return False\n',
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name, source in snippets.items():
                (root / name).write_text(source)
            detected = {site for site, node in _containment_functions(root).items() if _containment_candidate(node)}
        self.assertEqual({('resolve.py', 'copied'), ('realpath.py', 'copied')}, detected)

    def test_stale_allowlist_detects_removed_and_adopted_helpers(self):
        import ast
        site = ('example.py', 'guard')
        exemptions = {site: 'Previously separate policy.'}
        self.assertEqual({site}, _containment_stale_entries({}, exemptions))
        adopted = ast.parse('def guard(root, path):\n    return contained_resolved_path(root, path)\n').body[0]
        self.assertEqual({site}, _containment_stale_entries({site: adopted}, exemptions))


class ContainmentReloadTests(unittest.TestCase):
    def test_actual_reload_serves_modified_scratch_primitive(self):
        import json
        import os
        import subprocess
        probe = r'''
import json,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'tests'))
from server_tools_support import _make_repo,load_server,load_thin_runner
with tempfile.TemporaryDirectory() as temp:
    root=_make_repo(Path(temp))
    load_server()
    runner=load_thin_runner()
    runner.build_server(root)
    try:
        old=runner.server_impl.path_containment
        before,diagnostic=runner.server_impl.resolve_path_under_root(root,'contained-reload-probe')
        assert before is not None and diagnostic is None
        source=Path('path_containment.py')
        source.write_text(source.read_text()+'\n_original_comparison=contained_resolved_path\ndef contained_resolved_path(root,candidate):\n    if candidate.name == "contained-reload-probe":\n        return None\n    return _original_comparison(root,candidate)\n')
        result=runner.perform_mcp_reload()
        assert result['status']=='ok',result
        assert runner.server_impl.path_containment is not old
        after,diagnostic=runner.server_impl.resolve_path_under_root(root,'contained-reload-probe')
        assert after is None and diagnostic['code']=='path_outside_allowed_roots',(after,diagnostic)
        print(json.dumps({'fresh':True,'modified_comparison_served':True}))
    finally:
        runner._get_handler().close()
'''
        with tempfile.TemporaryDirectory() as temp:
            scratch = Path(temp) / 'scripts'
            shutil.copytree(SCRIPTS, scratch, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            result = subprocess.run([sys.executable, '-B', '-c', probe], cwd=scratch,
                env=dict(os.environ, PYTHONPATH=str(scratch), PYTHONDONTWRITEBYTECODE='1'),
                capture_output=True, text=True, timeout=120)
        self.assertEqual(0, result.returncode, result.stderr[-4000:])
        self.assertEqual({'fresh': True, 'modified_comparison_served': True},
                         json.loads(result.stdout.strip().splitlines()[-1]))


if __name__ == "__main__":
    unittest.main()
