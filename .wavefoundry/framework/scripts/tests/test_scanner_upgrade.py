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

if __name__ == '__main__':
    unittest.main()
