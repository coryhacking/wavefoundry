from pathlib import Path
from tempfile import TemporaryDirectory
import contextlib, io, json, os, shutil, sys
from unittest.mock import patch
import test_lifecycle_baseline_drift as t
import render_platform_surfaces as cli

with TemporaryDirectory() as temp:
    home=Path(temp)
    os.environ.update(HOME=temp,USERPROFILE=temp,CLAUDE_CONFIG_DIR=str(home/'claude'),CODEX_HOME=str(home/'codex'),WAVEFOUNDRY_MANAGED_SETTINGS_PATH=str(home/'managed'))
    case=t.BaselineDriftTests()
    case.setUp()
    try:
        for part in ('install','seeds'):
            shutil.copytree(t.SCRIPTS.parent /part,case.install.parent /part)
        case.put('docs/prompts/prompt-surface-manifest.json',json.dumps({'prompt_names':{key:t.renderer.vocabulary_profile.prompt_slug(key) for key in t.renderer.vocabulary_profile.DEFAULT_PROMPT_NAMES}}))
        t.renderer.render_agent_surfaces(case.root)
        template='lifecycle-prompts/implement-wave.prompt.md'
        prompt=case.root/t.IMPLEMENT
        marker=t.renderer.REVIEW_POLICY_SURFACE_MARKER_BEGIN
        assert marker in prompt.read_text()
        incoming=(case.install/template).read_text()+'\nIncoming baseline change.\n'
        rows=t.renderer.lifecycle_baseline_drift(case.root,{template:incoming})
        assert case.states(rows)[t.IMPLEMENT]=='upstream_changed_local_matches_previous'
        case.save_comparison(rows)
        (case.install/template).write_text(incoming)
        args=['--repo-root',str(case.root),'--platform','codex','--include-permissions','--manifest',str(home/'manifest.json')]
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            with patch.object(t.upgrade_lib,'update_upgrade_lock',return_value=False):
                try: result=cli.main(args)
                except RuntimeError as e: result=str(e)
            retry=cli.main(args)
        row=case.states(t.upgrade._lifecycle_baseline_findings(case.root))[t.IMPLEMENT]
        print('first result:',result,'retry:',retry,'incoming prose:', 'Incoming baseline change.' in prompt.read_text(),'review-policy marker present:',marker in prompt.read_text(),'reported:',row)
        assert result != 0 and retry == 0
        assert 'Incoming baseline change.' in prompt.read_text()
        assert marker in prompt.read_text() and row == 'replaced', 'Retry must restore the policy region and record the replacement'
    finally: case.doCleanups()
