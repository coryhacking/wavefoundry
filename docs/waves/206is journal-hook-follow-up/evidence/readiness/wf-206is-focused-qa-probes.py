import sys, ast, json, tempfile, hashlib, types, unittest, io
from pathlib import Path
from unittest.mock import patch
ROOT=Path('/Users/coryhacking/Developer/wavefoundry')
S=ROOT/'.wavefoundry/framework/scripts'
sys.path[:0]=[str(S),str(S/'tests')]
import test_upgrade_wavefoundry as u
import test_profile_support as p
packet=json.loads(Path('/tmp/wf-206is-readiness-focused-packet.json').read_text())
def digest(): return {n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in packet['scope_sha256']}
before=digest(); assert before==packet['scope_sha256']
results=[]
# Real checked-in declaration census, scratch proposed constant only; no product edit.
with tempfile.TemporaryDirectory() as d:
    d=Path(d); source=(S/'mcp_tool_extensions.py').read_text(); target=d/'mcp_tool_extensions.py'
    case=p.DefaultProfileOnlyMarkerTests('test_declaration_snapshot_covers_every_declaration_constant')
    with patch.object(p,'SCRIPTS_DIR',d):
        target.write_text(source); case.test_declaration_snapshot_covers_every_declaration_constant()
        target.write_text(source+'\nEXTENSION_JOURNAL_PRE_MIGRATION_TRIGGER = "legacy_cutover"\n')
        try: case.test_declaration_snapshot_covers_every_declaration_constant()
        except AssertionError as e: rejection=str(e)
        else: raise AssertionError('Expected exact production test to reject omitted registry')
        with patch.dict(p.SHIPPED_DECLARATION,{'EXTENSION_JOURNAL_PRE_MIGRATION_TRIGGER':'legacy_cutover'}):
            case.test_declaration_snapshot_covers_every_declaration_constant()
        results.append({'probe':'declaration_registry_scope','baseline':'accepted','omitted_new_constant':'rejected','error':rejection,'repair_control':'accepted with registry key','production_test':case.id()})
# Real existing gate and public preview, with extracted declaration source fixture.
for version in ('1.14.9','1.15.0','1.29.0'):
    f=u.JournalDeclarationMigrationTests('test_hook_runs_once_before_the_migration'); f.setUp()
    try:
        f._declare(hook='acme_journal_hooks:prepare',helpers=('acme_journal_hooks',),helper_source=f._hook_source(),extra='\nEXTENSION_JOURNAL_PRE_MIGRATION_TRIGGER = "journals_present"\nfrom pathlib import Path\nPath(__file__).parent.joinpath("declaration-executed").write_text("yes")\n')
        f._write_journal('kept.md','role journal kept\n'); f._gate(version)
        calls=len(f._hook_calls()); executed=(f.scripts/'declaration-executed').exists()
        assert calls==(1 if version=='1.14.9' else 0)
        assert executed==(version=='1.14.9')
        results.append({'probe':'current_gate_version_baseline','version':version,'calls':calls,'declaration_executed':executed,'journal_bytes':(f.journals/'kept.md').read_text()})
    finally:f.tearDown()
for trigger in ('"journals_present"','"typo"','str("journals_present")'):
    f=u.JournalDeclarationMigrationTests('test_hook_runs_once_before_the_migration'); f.setUp()
    try:
        f._declare(hook='acme_journal_hooks:prepare',helpers=('acme_journal_hooks',),helper_source=f._hook_source(),extra='\nEXTENSION_JOURNAL_PRE_MIGRATION_TRIGGER = '+trigger+'\nfrom pathlib import Path\nPath(__file__).parent.joinpath("declaration-executed").write_text("yes")\n')
        f._write_journal('kept.md','role journal kept\n')
        snapshot={str(x.relative_to(f.root)):x.read_bytes() for x in f.root.rglob('*') if x.is_file()}
        report=f.ext.migrate_journals(f.root,apply=False)
        after={str(x.relative_to(f.root)):x.read_bytes() for x in f.root.rglob('*') if x.is_file()}
        assert snapshot==after and f._hook_calls()==[] and not (f.scripts/'declaration-executed').exists()
        results.append({'probe':'public_preview_noexec','trigger':trigger,'target_bytes_unchanged':snapshot==after,'calls':0,'declaration_executed':False,'report':report,'limit':'Current preview ignores proposed trigger; no future trigger diagnostic proven'})
    finally:f.tearDown()
# Real failure->retry gate transition and cached sibling counterexample; first fails, retry returns.
f=u.JournalDeclarationMigrationTests('test_hook_runs_once_before_the_migration'); f.setUp()
try:
    name='qa206is_incoming_dep'
    incoming=f.scripts/(name+'.py'); incoming.write_text('VALUE = "INCOMING"\n')
    old=types.ModuleType(name); old.VALUE='OLD'; sys.modules[name]=old
    body='from '+name+' import VALUE\n    Path(root).joinpath("dependency.txt").write_text(VALUE)\n    if not Path(root).joinpath("retry-allowed").exists():\n        raise RuntimeError("private "+str(root))'
    f._declare(hook='acme_journal_hooks:prepare',helpers=(name,'acme_journal_hooks'),helper_source=f._hook_source(body))
    f._write_journal('kept.md','role journal kept\n'); before_j=(f.journals/'kept.md').read_bytes()
    with patch.object(f.ext,'_migrate_journals') as migration:
        warning=f._gate('1.14.9'); migration.assert_not_called()
    assert len(f._hook_calls())==1 and (f.journals/'kept.md').read_bytes()==before_j and str(f.root) not in warning
    observed=(f.root/'dependency.txt').read_text(); assert observed=='OLD'
    f.root.joinpath('retry-allowed').write_text('yes'); sys.modules.pop(name)
    with patch.object(f.ext,'_migrate_journals') as migration:
        f._gate('1.14.9'); migration.assert_called_once()
    assert len(f._hook_calls())==2 and (f.root/'dependency.txt').read_text()=='INCOMING'
    results.append({'probe':'failure_retry_cached_dependency','failed_attempt_calls':1,'retry_total_calls':2,'dependent_migration_after_failure':0,'dependent_migration_after_retry':1,'cached_observed':observed,'uncached_observed':'INCOMING','warning':warning,'limit':'Existing pre_docs_gate boundary, no actual old-runner full upgrade; unrelated fixture mechanisms already completed'})
finally:sys.modules.pop('qa206is_incoming_dep',None); f.tearDown()
# Independent selected regression checks, excludes known native-Windows-only test.
names=['JournalMigrationTests.test_pre_docs_gate_version_gates_journal_migration','JournalDeclarationMigrationTests.test_hook_is_not_called_after_1_15_or_by_the_preview','JournalDeclarationMigrationTests.test_invalid_declaration_leaves_the_memory_naming_migration_unapplied','JournalDeclarationMigrationTests.test_declaration_module_is_executed_once_per_gate','JournalStaticPreviewTests.test_unreadable_declaration_warns_once_and_leaves_template_journals','UpgradeExtensionSearchPathTests.test_pre_docs_gate_holds_the_path_across_the_hook_load_and_call']
suite=unittest.TestLoader().loadTestsFromNames(['test_upgrade_wavefoundry.'+n for n in names]); log=io.StringIO(); result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
assert result.wasSuccessful() and len(result.skipped)==0 and result.testsRun==len(names),log.getvalue()
results.append({'probe':'selected_regression_tests','tests':names,'run':result.testsRun,'skips':result.skipped,'log':log.getvalue()})
after=digest(); assert after==before
output={'results':results,'before_scope_sha256':before,'after_scope_sha256':after,'scope_unchanged':before==after}
Path('/tmp/wf-206is-focused-qa-probe-results.json').write_text(json.dumps(output,indent=2)+'\n')
print(json.dumps(output,indent=2))
