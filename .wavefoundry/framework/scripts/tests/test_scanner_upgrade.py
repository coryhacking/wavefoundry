"""Incoming scanner checks run before publishing framework or local rule bytes."""
from __future__ import annotations
import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.dont_write_bytecode = True
SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import scanner_upgrade as preflight
import upgrade_wavefoundry as upgrade


class IncomingScannerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = tempfile.TemporaryDirectory()
        cls.pack = Path(cls.scratch.name)/'incoming.zip'
        source = SCRIPTS.parents[2]
        with zipfile.ZipFile(cls.pack, 'w', zipfile.ZIP_DEFLATED) as archive:
            for path in (source/preflight.FRAMEWORK).rglob('*'):
                rel = path.relative_to(source).as_posix()
                if path.is_file() and preflight._selected(rel):
                    if rel.endswith('/scan-rules.toml'):
                        archive.writestr(rel, 'wavefoundryProfile="betterleaks-v2-8f376ff9"\n[[rules]]\nid="framework-fixture"\nregex="SYNTHETIC"\n')
                    else:
                        archive.write(path, rel)

    @classmethod
    def tearDownClass(cls):
        cls.scratch.cleanup()

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.local=self.root/preflight.PROJECT_RULES
        self.local.parent.mkdir(parents=True)
        self.installed=self.root/preflight.FRAMEWORK/'scan-rules.toml'
        self.installed.parent.mkdir(parents=True)
        self.installed.write_text('[[rules]]\nid="old"\nregex="SYNTHETIC"\n')

    def inspect(self, text):
        self.local.write_text(text)
        before=self.local.read_bytes(),self.installed.read_bytes()
        result=preflight.inspect_project_rules(self.root,self.pack)
        self.assertEqual(before,(self.local.read_bytes(),self.installed.read_bytes()))
        return result

    def test_absent_and_allowlist_only_and_valid_custom_are_compatible(self):
        self.assertEqual(preflight.inspect_project_rules(self.root,self.pack)['status'],'not_applicable')
        for config in ('[allowlist]\npaths=["^safe/"]\n', '[[rules]]\nid="custom"\nregex="SYNTHETIC_OTHER"\nvalueGroup=0\nfilter="false"\n'):
            with self.subTest(config=config):
                self.assertEqual(self.inspect(config)['status'],'compatible')

    def test_old_fields_and_cel_are_rejected_with_safe_exact_location(self):
        for field, value in (('secretGroup','1'),('withinLines','3'),('filter','"secret.contains(\\\"example\\\")"')):
            with self.subTest(field=field):
                result=self.inspect(f'[[rules]]\nid="project-rule"\nregex="SYNTHETIC"\n{field}={value}\n')
                self.assertEqual(result['status'],'unsupported',result)
                self.assertEqual(result['issues'][0]['field'],field)
                self.assertEqual(result['issues'][0]['rule'],'project-rule')
                self.assertNotIn('example',str(result))
        result=self.inspect('filter="true"\n')
        self.assertEqual(result['issues'][0]['field'],'filter')

    def test_malformed_rule_ids_never_serialize_configuration_values(self):
        marker = 'SYNTHETIC_PRIVATE_SENTINEL_22QKY'
        for value in ('{private="' + marker + '"}', '["' + marker + '"]',
                      '42', 'true', '""'):
            with self.subTest(value=value):
                result = self.inspect(
                    f'[[rules]]\nid={value}\nregex="SYNTHETIC"\nsecretGroup=1\n')
                self.assertEqual(result['status'], 'unsupported')
                self.assertNotIn(marker, str(result))
                self.assertEqual(result['issues'][0], {
                    'file': preflight.PROJECT_RULES, 'field': 'id',
                    'code': 'invalid_rule_id', 'rule': 'rules[0]'})
                self.assertEqual(result['issues'][1]['rule'], 'rules[0]')

    def test_existing_runner_preview_and_preflight_refuse_before_mutation(self):
        self.local.write_text('[[rules]]\nid="local"\nregex="SYNTHETIC"\nsecretGroup=1\n')
        before=self.local.read_bytes(),self.installed.read_bytes()
        with contextlib.ExitStack() as stack:
            for name, value in (('_report_pending_upgrade',None),('_check_installed_review_plan_prompt',None),('_detect_dashboard',(False,None,None)),('_read_installed_revision','1.39.0'),('_read_zip_version','1.40.0')):
                stack.enter_context(patch.object(upgrade,name,return_value=value))
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
            self.assertEqual(upgrade.phase_dry_run(self.root,explicit_pack=self.pack),3)
            import upgrade_protocol
            import upgrade_lib
            stack.enter_context(patch.object(upgrade_protocol,'validate_feature_pack',return_value={}))
            stack.enter_context(patch.object(upgrade_protocol,'runner_compatibility',return_value='compatible'))
            stack.enter_context(patch.object(upgrade_lib,'read_upgrade_lock',return_value=None))
            with self.assertRaises(SystemExit) as raised:
                upgrade.phase_preflight(self.root,True,explicit_pack=self.pack,retained_recovery=True)
            self.assertEqual(raised.exception.code,3)
        self.assertEqual(before,(self.local.read_bytes(),self.installed.read_bytes()))

    def test_changed_project_during_preflight_and_failed_worker_are_incomplete(self):
        self.local.write_text('[policy]\nfalse_positive_confirmations_required=1\n')
        import subprocess_util
        with patch.object(subprocess_util,'run_with_tree_kill',side_effect=TimeoutError):
            result=preflight.inspect_project_rules(self.root,self.pack)
        self.assertEqual(result['status'],'incomplete')
        original=preflight._read_rules
        count=[0]
        def changed(path):
            result=original(path);count[0]+=1
            return result+b'\n# concurrent edit' if count[0]>1 else result
        with patch.object(preflight,'_read_rules',side_effect=changed):
            result=preflight.inspect_project_rules(self.root,self.pack)
        self.assertEqual(result['status'],'incomplete')
        self.assertEqual(result['issues'][0]['code'],'project_rules_changed')

    def test_staging_refuses_traversal_and_excess_without_writing_target(self):
        self.local.write_text('[policy]\nfalse_positive_confirmations_required=1\n')
        bad=Path(self.tmp.name)/'bad.zip'
        with zipfile.ZipFile(bad,'w') as archive:
            archive.writestr(preflight.FRAMEWORK+'/scripts/../../escape.py','raise RuntimeError()')
        self.assertEqual(preflight.inspect_project_rules(self.root,bad)['status'],'incomplete')
        self.assertFalse((self.root/'escape.py').exists())
        with patch.object(preflight,'MAX_STAGE_BYTES',1):
            self.assertEqual(preflight.inspect_project_rules(self.root,self.pack)['status'],'incomplete')

    def test_pack_missing_a_scanner_module_is_incomplete_not_installed_fallback(self):
        # Change 22qr4: `lifecycle_id` is imported by the scanner and is not a
        # child bootstrap module, so only the installed copy could supply it.
        missing=preflight.FRAMEWORK+'/scripts/lifecycle_id.py'
        partial=Path(self.tmp.name)/'partial.zip'
        with zipfile.ZipFile(self.pack) as source, zipfile.ZipFile(partial,'w') as archive:
            names=source.namelist()
            self.assertIn(missing,names)
            for name in names:
                if name!=missing:
                    archive.writestr(name,source.read(name))
        config='[[rules]]\nid="custom"\nregex="SYNTHETIC_OTHER"\n'
        self.assertEqual(self.inspect(config)['status'],'compatible')
        import os
        for env in ({}, {'PYTHONPATH': str(SCRIPTS)}):
            with self.subTest(env=env), patch.dict(os.environ, env):
                self.local.write_text(config)
                result=preflight.inspect_project_rules(self.root,partial)
                self.assertEqual(result['status'],'incomplete',result)
                self.assertEqual(result['issues'][0]['code'],'incoming_validator_unavailable')

    def test_staged_import_path_drops_installed_and_inherited_scripts(self):
        import os
        staged=Path(self.tmp.name)/'staged'
        with patch.dict(os.environ,{'PYTHONPATH':os.pathsep.join([str(SCRIPTS),self.tmp.name])}), \
             patch.object(sys,'path',[str(SCRIPTS),self.tmp.name,*sys.path]):
            kept=preflight._staged_import_path(staged)
        self.assertEqual(kept[0],str(staged))
        real=lambda p: os.path.normcase(os.path.realpath(p))
        self.assertNotIn(real(SCRIPTS),[real(p) for p in kept[1:]])
        self.assertNotIn(real(self.tmp.name),[real(p) for p in kept[1:]])
        import json as stdlib_json
        self.assertIn(real(Path(stdlib_json.__file__).parents[1]),[real(p) for p in kept])


class ProjectRulesParseErrorTests(unittest.TestCase):
    """Change 22r96 (AC-2): a broken project rule file is named as such."""

    # Share the incoming-pack fixture without rerunning its tests.
    setUpClass = classmethod(IncomingScannerTests.setUpClass.__func__)
    tearDownClass = classmethod(IncomingScannerTests.tearDownClass.__func__)
    setUp = IncomingScannerTests.setUp
    inspect = IncomingScannerTests.inspect

    BROKEN = '[[rules]\nid="SYNTHETIC_PARSE_SENTINEL_22R96"\nregex="SYNTHETIC"\n'

    def assert_no_parser_or_file_text(self, result):
        text = str(result)
        for leaked in ('SYNTHETIC_PARSE_SENTINEL_22R96', 'regex', 'line 1', 'Expected', 'column'):
            self.assertNotIn(leaked, text)

    def inspect_root_in_process(self, project, framework='wavefoundryProfile="betterleaks-v2-8f376ff9"\n[[rules]]\nid="framework-fixture"\nregex="SYNTHETIC"\n'):
        self.local.write_text(project)
        self.installed.write_text(framework)
        from wave_lint_lib import betterleaks_worker
        self.addCleanup(betterleaks_worker.close_worker)
        with patch.object(sys, 'path', list(sys.path)):  # _inspect_root replaces sys.path.
            return preflight._inspect_root(self.root)

    def test_parse_error_is_named_by_both_entry_points_without_parser_text(self):
        result = self.inspect(self.BROKEN)
        self.assertEqual(result['issues'], [{'file': preflight.PROJECT_RULES, 'field': '$', 'code': 'project_rules_parse_error'}], result)
        self.assert_no_parser_or_file_text(result)
        child = self.inspect_root_in_process(self.BROKEN)
        self.assertEqual([i['code'] for i in child['issues']], ['project_rules_parse_error'], child)
        self.assertEqual(child['status'], result['status'])
        # An operator-fixable rule-file defect, not a validator outage.
        self.assertEqual(result['status'], 'unsupported', result)
        self.assert_no_parser_or_file_text(child)

    def test_other_worker_failures_and_a_broken_framework_file_keep_validator_unavailable(self):
        from wave_lint_lib import secrets_validators as scanner
        from wave_lint_lib import betterleaks_worker as live
        original = scanner._load_toml

        def project_timeout(path):
            if Path(path) == self.local:
                raise live.WorkerError('worker_timeout')
            return original(path)
        for raised in (project_timeout, lambda path: (_ for _ in ()).throw(live.WorkerError('worker_input_too_large')),
                       lambda path: (_ for _ in ()).throw(ValueError('configuration_size_limit')),
                       lambda path: (_ for _ in ()).throw(UnicodeDecodeError('utf-8', b'\xff', 0, 1, 'x'))):
            with self.subTest(raised=raised), patch.object(scanner, '_load_toml', side_effect=raised):
                child = self.inspect_root_in_process('[[rules]]\nid="custom"\nregex="SYNTHETIC_OTHER"\n')
                self.assertEqual([i['code'] for i in child['issues']], ['incoming_validator_unavailable'], child)
        child = self.inspect_root_in_process('[[rules]]\nid="custom"\nregex="SYNTHETIC_OTHER"\n', framework='[[rules]\n')
        self.assertEqual([i['code'] for i in child['issues']], ['incoming_validator_unavailable'], child)
        broken = Path(self.tmp.name)/'broken-framework.zip'
        with zipfile.ZipFile(self.pack) as source, zipfile.ZipFile(broken, 'w') as archive:
            for name in source.namelist():
                archive.writestr(name, '[[rules]\n' if name.endswith('/scan-rules.toml') and '/scan/' not in name else source.read(name))
        self.local.write_text('[[rules]]\nid="custom"\nregex="SYNTHETIC_OTHER"\n')
        result = preflight.inspect_project_rules(self.root, broken)
        self.assertEqual([i['code'] for i in result['issues']], ['incoming_validator_unavailable'], result)

if __name__ == '__main__':
    unittest.main()
