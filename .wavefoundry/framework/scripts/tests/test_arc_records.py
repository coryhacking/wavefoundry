"""Arc records share IDs and profile naming, without delivery lifecycle state."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import lifecycle_id
import record_paths as rp
import vocabulary_profile as vp
import render_agent_surfaces as ras
from record_layout_support import apply_profile, copy_scripts_tree, default_profile_only


@default_profile_only("checks the shipped Arc contract and its Epic distribution override")
class ArcRecordTests(unittest.TestCase):
    def test_path_and_shared_id_collision(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'docs').mkdir()
            (root / 'docs/workflow-config.json').write_text(json.dumps({'lifecycle_id_policy': {
                'scheme_version': 'v2', 'epoch_utc': '2026-11-01T00:00:00Z', 'offset': 46656}}))
            env = dict(os.environ, PROJECT_ROOT=str(root), PYTHONDONTWRITEBYTECODE='1')
            env.pop('PYTHONPYCACHEPREFIX', None)
            command = [sys.executable, '-B', str(SCRIPTS / 'lifecycle_id.py'), '--kind', 'arc',
                       '--slug', 'shared-outcome', '--unix-seconds', '1793664000']
            first = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            identifier = first.stdout.strip()
            path = rp.arc_record_path(root, identifier)
            prefix = identifier.split('-')[0]
            self.assertEqual(path.relative_to(root).as_posix(),
                             f'docs/arcs/{prefix} shared-outcome/{identifier}.md')
            path.parent.mkdir(parents=True)
            path.write_text('# Outcome\nOperator-owned content.\n')
            second = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertNotEqual(second.stdout.strip().split('-')[0], prefix)
            self.assertIn(prefix, lifecycle_id._existing_prefixes(root))
            self.assertEqual(path.read_text(), '# Outcome\nOperator-owned content.\n')
            self.assertNotIn('arc', vp.CHANGE_KINDS)
            self.assertEqual(lifecycle_id.build_id('wave', 'sample', legacy=True), '00000 sample')
            self.assertEqual(lifecycle_id.build_id('enh', 'sample', legacy=True), '00000-enh sample')

    def test_record_path_rejects_unsafe_names_roots_and_links(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for identifier in ('12345-arc ../escape', '12345-wave sample', '12345-arc a/b'):
                with self.subTest(identifier=identifier), self.assertRaises(rp.RecordLayoutInvalid):
                    rp.arc_record_path(root, identifier)
            for bad_root in ('../arcs', '/arcs', 'docs/waves', 'docs/plans/arcs'):
                with self.subTest(root=bad_root), mock.patch.object(rp, 'ARCS_ROOT', bad_root):
                    with self.assertRaises(rp.RecordLayoutInvalid):
                        rp.arc_record_path(root, '12345-arc sample')

    def test_record_path_rejects_linked_folder(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'docs/arcs').mkdir(parents=True)
            (root / 'elsewhere').mkdir()
            try:
                (root / 'docs/arcs/12345 sample').symlink_to(root / 'elsewhere', target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f'host cannot create directory symlink: {type(exc).__name__}')
            with self.assertRaises(rp.RecordLayoutInvalid):
                rp.arc_record_path(root, '12345-arc sample')

    def test_unreadable_arc_listing_refuses_id_mint(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            top = root / rp.ARCS_ROOT
            top.mkdir(parents=True)
            original = rp._scandir
            def denied(path):
                if path == top:
                    raise PermissionError('fixture')
                return original(path)
            with mock.patch.object(rp, '_scandir', side_effect=denied):
                with self.assertRaises(rp.RecordRootUnreadable):
                    lifecycle_id._existing_prefixes(root)

    def test_arc_folder_and_document_ids_both_reserve_prefixes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / rp.ARCS_ROOT / '12345 sample'
            folder.mkdir(parents=True)
            (folder / '12346-arc older-reference.md').write_text('# Retained reference\n')
            self.assertTrue({'12345', '12346'} <= lifecycle_id._existing_prefixes(root))

    def test_arc_vocabulary_collisions(self):
        for kind in ('wave', 'enh', 'mem', '../epic', 'Epic'):
            with self.subTest(kind=kind), mock.patch.object(vp, 'ARC_KIND', kind):
                self.assertTrue(vp.arc_vocabulary_errors())
        with mock.patch.object(vp, 'ARC_NAME', vp.CONTAINER_NAME):
            self.assertTrue(vp.arc_vocabulary_errors())
        self.assertTrue(vp.prompt_name_errors({'plan-change': {'slug': 'plan-arc', 'shortcut': 'Different'}}))
        self.assertTrue(vp.prompt_name_errors({'plan-change': {'slug': 'other', 'shortcut': 'Plan initiative'}}))

    def test_registered_legacy_prompt_moves_bytes_and_conflicts_preserve_both(self):
        for conflict in (False, True):
            with self.subTest(conflict=conflict), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                (root / 'docs/prompts').mkdir(parents=True)
                manifest = root / ras.PROMPT_SURFACE_MANIFEST
                manifest.write_text(json.dumps({'public_prompt_surface': [{
                    'doc': 'docs/prompts/plan-initiative.prompt.md', 'shortcut': 'Plan initiative'}]}))
                old = root / 'docs/prompts/plan-initiative.prompt.md'
                new = root / vp.prompt_doc('plan-arc')
                content = b'# Custom initiative\r\nKeep this local policy.\r\n'
                old.write_bytes(content)
                if conflict:
                    new.write_text('# Different local draft\n')
                    before = manifest.read_bytes()
                    with self.assertRaisesRegex(RuntimeError, 'both exist'):
                        ras.migrate_profile_prompt_names(root)
                    self.assertEqual(old.read_bytes(), content)
                    self.assertEqual(new.read_text(), '# Different local draft\n')
                    self.assertEqual(manifest.read_bytes(), before)
                else:
                    ras.migrate_profile_prompt_names(root)
                    self.assertFalse(old.exists())
                    self.assertEqual(new.read_bytes(), content)
                    self.assertEqual(json.loads(manifest.read_text())['public_prompt_surface'][0]['doc'],
                                     vp.prompt_doc('plan-arc'))
                    self.assertEqual(ras.migrate_profile_prompt_names(root).written, ())

    def test_unregistered_legacy_file_is_not_adopted_by_renderer(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'docs/prompts').mkdir(parents=True)
            (root / ras.PROMPT_SURFACE_MANIFEST).write_text('{}')
            old = root / 'docs/prompts/plan-initiative.prompt.md'
            old.write_text('Operator content')
            ras.migrate_profile_prompt_names(root)
            self.assertEqual(old.read_text(), 'Operator content')
            self.assertFalse((root / vp.prompt_doc('plan-arc')).exists())

    def test_optional_arc_prompt_is_not_required_before_authoring(self):
        from wave_lint_lib.core_validators import check_required_files
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'docs').mkdir()
            failures = check_required_files(root)
            self.assertTrue(failures)  # Real producer ran against an unseeded target.
            self.assertFalse(any('plan-arc' in failure for failure in failures))
            self.assertFalse((root / vp.prompt_doc('plan-arc')).exists())

    def test_epic_profile_cli_path_and_skill(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            scripts = copy_scripts_tree(root / '.wavefoundry/framework')
            profile = {'modules': {
                'vocabulary_profile': {'ARC_NAME': 'Epic', 'ARC_KIND': 'epic', 'PROMPT_NAME_OVERRIDES': {
                    'plan-arc': {'slug': 'plan-epic', 'shortcut': 'Plan epic', 'aliases': ['Plan initiative']}}},
                'record_paths': {'ARCS_ROOT': 'docs/epics'}}}
            apply_profile(scripts, profile, repo_root=root, python=sys.executable)
            (root / 'docs/prompts').mkdir(parents=True, exist_ok=True)
            (root / 'docs/prompts/prompt-surface-manifest.json').write_text(json.dumps({
                'public_prompt_surface': [{'doc':'docs/prompts/plan-initiative.prompt.md','shortcut':'Plan initiative'}]}))
            old = root / 'docs/prompts/plan-initiative.prompt.md'
            old.write_bytes(b'# Local policy\r\nKeep custom content.\r\n')
            (root / '.codex').mkdir()
            code = '''import json,sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import vocabulary_profile as v, record_paths as r, render_agent_surfaces as a, lifecycle_id as l
root=Path(sys.argv[2])
args=l.parse_args(['--kind','epic','--slug','shared-outcome','--legacy'])
id=l.build_id(args.kind,args.slug,legacy=args.legacy,repo_root=root)
p=r.arc_record_path(root,id)
a.migrate_profile_prompt_names(root)
a.render_skills(root)
print(json.dumps({'id':id,'path':p.relative_to(root).as_posix(),'kind_is_change':v.ARC_KIND in v.CHANGE_KINDS,'skill':v.skill_name('plan-arc'),'prompt':v.prompt_doc('plan-arc')}))
'''
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
            env.pop('PYTHONPYCACHEPREFIX', None)
            result = subprocess.run([sys.executable, '-B', '-c', code, str(scripts), str(root)],
                                    env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = json.loads(result.stdout)
            self.assertEqual(result['path'], 'docs/epics/00000 shared-outcome/00000-epic shared-outcome.md')
            self.assertFalse(result['kind_is_change'])
            self.assertEqual(result['skill'], 'wf-plan-epic')
            self.assertEqual(result['prompt'], 'docs/prompts/plan-epic.prompt.md')
            self.assertEqual((root / result['prompt']).read_bytes(), b'# Local policy\r\nKeep custom content.\r\n')
            skill = (root / '.codex/skills/wf-plan-epic/SKILL.md').read_text()
            self.assertIn('docs/prompts/plan-epic.prompt.md', skill)
            self.assertNotIn('plan-arc.prompt.md', skill)
            self.assertFalse((root / '.codex/skills/wf-plan-initiative').exists())
            self.assertFalse((root / 'docs/epics').exists())


if __name__ == '__main__':
    unittest.main()
